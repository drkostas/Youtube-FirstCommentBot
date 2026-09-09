from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_basicauth import BasicAuth

from youbot import Configuration, YoutubeManager
import traceback
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

app.config["BASIC_AUTH_USERNAME"] = os.getenv("BASIC_AUTH_USERNAME")
app.config["BASIC_AUTH_PASSWORD"] = os.getenv("BASIC_AUTH_PASSWORD")
basic_auth = BasicAuth(app)

# This dashboard now runs at home against a local copy of its database, reachable over
# Tailscale. The hosted copy is kept only so its address still answers: when RETIRED_NOTICE is
# set it serves that notice for every address and never opens a database connection, which is
# what lets the Amazon instance it used to talk to be closed off and deleted.
#
# ⭐ ANSWERED BEFORE THE REQUEST IS DISPATCHED, NOT AS A CATCH-ALL ROUTE. Flask prefers a static
# rule like /get_comments over a path converter, so a catch-all would leave every named page
# still running its own handler. before_request covers every address, including the ones behind
# the password.
RETIRED_NOTICE = os.getenv("RETIRED_NOTICE")
if RETIRED_NOTICE:
    from flask import Response

    @app.before_request
    def _retired_before_request():
        return Response(RETIRED_NOTICE + "\n", status=410, mimetype="text/plain")


# Config
config_file = "confs/accumulator.yml"
conf_obj = Configuration(config_src=config_file)
you_conf = conf_obj.get_config("youtube")[0]
db_conf = conf_obj.get_config("datastore")[0]["config"]
cloud_conf = None  # conf_obj.get_config("cloudstore")[0]


app.config[
    "SQLALCHEMY_DATABASE_URI"
] = f"mysql+pymysql://{db_conf['username']}:{db_conf['password']}@{db_conf['hostname']}:{db_conf['port']}/{db_conf['db_name']}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ⛔ IT WAS THE QUERY AT IMPORT, NOT THE MANAGER. This module used to end with
# `channel_data = ytm.db.get_channels(...)`, so every cold start opened a database connection
# before any route was matched. With the database unreachable that did not fail, it HUNG until
# the platform killed it, and the address returned 504 and then 500 — which is what happened the
# moment the Amazon instance was closed off. Nothing ever read that list.
#
# ⚠️ THE MANAGER ITSELF CANNOT BE MADE LAZY. Building it registers the SQLAlchemy extension,
# which calls `app.teardown_appcontext`, and Flask refuses that once the app has served its first
# request ("can no longer be called on the application"). So it is built here, at import, where
# it opens no connection — and only when the notice is unset, so the retired copy stays clean.
_ytm = (
    None
    if RETIRED_NOTICE
    else YoutubeManager(
        config=you_conf["config"],
        db_conf={"type": "flask_mysql", "app": app},
        cloud_conf=cloud_conf,
        api_type=you_conf["type"],
        tag=conf_obj.tag,
        log_path="logs/accumulator.log",
    )
)


def manager():
    """The YouTube manager. Absent only on the retired copy, which never reaches a route."""
    if _ytm is None:
        raise RuntimeError("this copy is retired and has no database")
    return _ytm



@app.route("/run_accumulator", methods=["POST"])
def run_accumulator():
    cron_secret = os.getenv("CRON_SECRET")
    # Get the Authorization header from the request
    auth_header = request.headers.get("Authorization")

    # Check if the Authorization header matches the expected format
    if not auth_header or auth_header != f"Bearer {cron_secret}":
        return jsonify({"error": "Unauthorized"}), 401
    num_comments_to_check = request.json.get("num_comments_to_check")  # type: ignore
    try:
        results = manager().accumulator_step(num_comments_to_check)
        return (
            jsonify(
                {
                    "message": (
                        "Accumulator completed successfully"
                        f" ({results['exceptions']}/{results['cnt']} exceptions)"
                    )
                }
            ),
            200,
        )
    except Exception as e:
        full_error = f"{str(e)} : {traceback.format_exc()}"
        print(full_error)
        return jsonify({"error": full_error}), 500


@app.route("/get_channels", methods=["GET"])
@basic_auth.required
def get_channels():
    try:
        channel_data = manager().db.get_channels(
            channel_cols=[
                "channel_id",
                "username",
                "active",
                "self_comments_only",
                "last_commented",
                "delay_comment",
                "priority",
                "channel_photo",
            ],
            where="True",
            extra_stats=True,  # type: ignore
        )

        return jsonify(list(channel_data))
    except Exception as e:
        full_error = f"{str(e)} : {traceback.format_exc()}"
        print(full_error)
        return jsonify({"error": full_error}), 500


@app.route("/update_channel", methods=["POST"])
@basic_auth.required
def update_channel():
    channel_id = request.json.get("channel_id")  # type: ignore
    priority = request.json.get("priority")  # type: ignore
    delay = request.json.get("delay_comment")  # type: ignore

    if not channel_id or priority is None or delay is None:
        return jsonify({"error": "Missing channel_id or priority or delay"}), 400

    try:
        channel_data = {"channel_id": channel_id}
        manager().db.update_delay_comment(channel_id=channel_id, delay=delay)  # type: ignore
        manager().db.set_priority(channel_data=channel_data, priority=priority)
        return (
            jsonify(
                {
                    "message": (
                        f"Channel {channel_id} priority set to {priority} and delay to"
                        f" {delay}"
                    )
                }
            ),
            200,
        )
    except Exception as e:
        full_error = f"{str(e)} : {traceback.format_exc()}"
        print(full_error)
        return jsonify({"error": full_error}), 500


@app.route("/add_channel", methods=["POST"])
@basic_auth.required
def add_channel():
    channel_data = request.json

    if not channel_data:
        return jsonify({"error": "No channel data provided"}), 400

    try:
        manager().add_channel(channel_id=channel_data["channel_id"])
        return jsonify({"message": "Channel added successfully"}), 201
    except Exception as e:
        full_error = f"{str(e)} : {traceback.format_exc()}"
        return jsonify({"error": full_error}), 500


@app.route("/get_comments", methods=["GET"])
@basic_auth.required
def get_comments():
    n_recent = request.args.get("n_recent", 50, type=int)
    min_likes = request.args.get("min_likes", -1, type=int)
    max_likes = request.args.get("max_likes", 99999, type=int)
    min_replies = request.args.get("min_replies", -1, type=int)
    max_replies = request.args.get("max_replies", 99999, type=int)
    channel_id = request.args.get("channel_id", None, type=str)
    only_null_upload = request.args.get("only_null_upload", False, type=bool)
    only_null_comment_id = request.args.get("only_null_comment_id", False, type=bool)
    only_null_video_title = request.args.get("only_null_video_title", False, type=bool)

    comments = manager().db.get_comments(
        comment_cols=[
            "video_title",
            "comment",
            "like_count",
            "reply_count",
            "comment_link",
            "video_link",
            "upload_time",
            "comment_time",
        ],
        channel_cols=["channel_photo", "username"],
        n_recent=n_recent,
        min_likes=min_likes,
        max_likes=max_likes,
        min_replies=min_replies,
        max_replies=max_replies,
        channel_id=channel_id,  # type: ignore
        only_null_upload=only_null_upload,
        only_null_comment_id=only_null_comment_id,
        only_null_video_title=only_null_video_title,
    )
    return jsonify(list(comments))


@app.route("/refresh_photos", methods=["POST"])
@basic_auth.required
def refresh_photos():
    try:
        updated = manager().refresh_photos()
        return jsonify({"message": f"{updated} channel photos refreshed"}), 200
    except Exception as e:
        full_error = f"{str(e)} : {traceback.format_exc()}"
        print(full_error)
        return jsonify({"error": full_error}), 500


@app.route(f"/toggle_active/<channel_id>", methods=["POST"])
@basic_auth.required
def toggle_active(channel_id):
    if not channel_id:
        return jsonify({"error": "Missing channel_id"}), 400

    try:
        current_status = manager().db.get_channel_by_id(channel_id)["active"]
        new_status = int(not current_status)

        if new_status:
            delay = 10
            priority = 999
        else:
            delay = 9999
            priority = 9999

        manager().db.update_channel_status(  # type: ignore
            channel_id=channel_id, new_status=new_status, delay=delay, priority=priority
        )

        return (
            jsonify(
                {"message": f"Channel {channel_id} active status set to {new_status}"}
            ),
            200,
        )
    except Exception as e:
        full_error = f"{str(e)} : {traceback.format_exc()}"
        print(full_error)
        return jsonify({"error": full_error}), 500


@app.route("/")
@basic_auth.required
def home():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True, port=8000)
