from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func, case, text, distinct
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Union
from youbot import ColorLogger
import time
from datetime import datetime, timedelta

logger = ColorLogger(logger_name="YoutubeMySqlDatastore", color="red")

db = SQLAlchemy()


class Channel(db.Model):
    __tablename__ = "channels"
    channel_id = db.Column(db.String(100), primary_key=True, nullable=False, default="")
    username = db.Column(db.String(100), nullable=False)
    added_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_commented = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    priority = db.Column(db.Integer, nullable=False, default=0)
    channel_photo = db.Column(db.String(100), default="-1")
    active = db.Column(db.Boolean, default=True)
    self_comments_only = db.Column(db.Boolean, default=False)
    delay_comment = db.Column(db.Integer, default=10)

    def to_dict(self):
        """
        Convert the Channel instance into a dictionary, handling the date string conversion.
        """

        # Define a function to safely parse datetime strings
        def parse_datetime(date_string):
            # Specify the format if it's known, or use a parser like dateutil if the format varies
            date_format = "%Y-%m-%dT%H:%M:%S"  # Example format, adjust as necessary
            try:
                return datetime.strptime(date_string, date_format).isoformat()
            except (ValueError, TypeError):
                return None

        # Convert added_on and last_commented to datetime if they are not None
        added_on_iso = parse_datetime(self.added_on) if self.added_on else None
        last_commented_iso = (
            parse_datetime(self.last_commented) if self.last_commented else None
        )

        return {
            "channel_id": self.channel_id,
            "username": self.username,
            "added_on": added_on_iso,
            "last_commented": last_commented_iso,
            "priority": self.priority,
            "channel_photo": self.channel_photo,
            "active": self.active,
            "self_comments_only": self.self_comments_only,
            "delay_comment": self.delay_comment,
        }


class Comment(db.Model):
    __tablename__ = "comments"
    video_link = db.Column(db.String(100), primary_key=True, nullable=False)
    channel_id = db.Column(db.String(100), db.ForeignKey("channels.channel_id"))
    comment = db.Column(db.String(255), nullable=False)
    comment_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    upload_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    like_count = db.Column(db.Integer, default=-1)
    reply_count = db.Column(db.Integer, default=-1)
    comment_id = db.Column(db.String(100), default="-1")
    video_id = db.Column(db.String(100), default="-1")
    comment_link = db.Column(db.String(100), default="-1")
    video_title = db.Column(db.String(255), default="-1")
    channel = db.relationship("Channel", backref=db.backref("comments", lazy=True))

    def to_dict(self):
        """
        Convert the Comment instance into a dictionary.
        """
        return {
            "channel_id": self.channel_id,
            "video_link": self.video_link,
            "comment": self.comment,
            "comment_time": self.comment_time.isoformat()
            if self.comment_time
            else None,
            "upload_time": self.upload_time.isoformat() if self.upload_time else None,
            "like_count": self.like_count,
            "reply_count": self.reply_count,
            "comment_id": self.comment_id,
            "video_id": self.video_id,
            "comment_link": self.comment_link,
            "video_title": self.video_title,
        }


class YoutubeFlaskMySqlDatastore:
    def __init__(self, app, create_all=False):
        """
        The basic constructor. Creates a new instance of Datastore using the specified credentials
        :param config:
        :param tag:
        """

        self.app = app
        db.init_app(app)
        
        if create_all:
            with self.app.app_context():
                db.create_all()
        

    def get_channels(
        self,
        channel_cols: List[str],
        comment_cols: Optional[List[str]] = None,
        extra_stats: bool = False,
        where: str = "Channel.active == 1",
        join_type: str = "left",
        complex_sort_key: Optional[int] = None,
    ) -> List[Dict]:
        """Retrieve all channels from the database."""
        with self.app.app_context():
            query = db.session.query(Channel)

            # ⚠️ ONLY WHEN COMMENT COLUMNS ARE ACTUALLY ASKED FOR. This used to join the comments
            # table for extra_stats as well, which the statistics do not need: they come from the
            # aggregated subquery below, already grouped by channel. The extra join multiplied
            # every channel by its comment count — 108 channels arrived as 22,339 rows, and the
            # ORM then discarded 22,231 of them as duplicates of the same entities. Invisible on a
            # local socket; over HTTPS from Vercel it was the difference between a page and a
            # timeout.
            if comment_cols:
                CommentModel = db.aliased(Comment)
                query = query.outerjoin(
                    CommentModel, Channel.channel_id == CommentModel.channel_id
                )

                # Add columns from the comment model if needed
                if comment_cols:
                    for col in comment_cols:
                        query = query.add_columns(getattr(CommentModel, col))

            if extra_stats:
                # Subquery for recent comments
                recent_comments_subq = (
                    db.session.query(
                        Comment.channel_id,
                        db.func.count(Comment.comment_id).label("count"),
                        db.func.avg(Comment.like_count).label("avg_likes"),
                        db.func.avg(Comment.reply_count).label("avg_replies"),
                        # db.func.max(Comment.comment_time).label('last_comment_date'),
                        db.func.sum(
                            db.case((Comment.like_count <= 0, 1), else_=0)
                        ).label("banned_count"),
                    )
                    .filter(Comment.comment_time > datetime.now() - timedelta(days=30))
                    .group_by(Comment.channel_id)
                    .subquery()
                )

                # Add extra statistics columns
                query = query.add_columns(
                    recent_comments_subq.c.count,
                    recent_comments_subq.c.avg_likes,
                    recent_comments_subq.c.avg_replies,
                    # recent_comments_subq.c.last_comment_date,
                    recent_comments_subq.c.banned_count,
                ).outerjoin(
                    recent_comments_subq,
                    Channel.channel_id == recent_comments_subq.c.channel_id,
                )

            # Add columns from the channel model
            for col in channel_cols:
                query = query.add_columns(getattr(Channel, col))

            # Apply the where condition
            query = query.filter(eval(where))

            # Order by, if necessary
            if complex_sort_key is None:
                query = query.order_by(Channel.delay_comment, Channel.priority)

            # Execute the query and convert results to dictionary
            results = query.all()
            return [
                {k: v for k, v in result._asdict().items() if k != "Channel"}
                for result in results
            ]

    def add_channel(
        self, channel_data: Dict, active: bool = True, delay_comment=20, priority=999
    ) -> None:
        """Insert the provided channel into the database"""
        with self.app.app_context():
            try:
                new_channel = Channel(**channel_data)
                new_channel.active = active
                new_channel.delay_comment = delay_comment
                new_channel.priority = priority
                db.session.add(new_channel)
                db.session.commit()
            except Exception as e:
                logger.error(f"Database error: {e}")

    def set_priority(self, channel_data: Dict, priority: Union[str, int]) -> None:
        """Set the priority of a given channel and adjust priorities of others"""
        start_time = time.time()

        new_priority = int(priority)

        with self.app.app_context():
            req_channel_id = channel_data["channel_id"]
            try:
                # Get the channel that needs to update its priority
                channel_to_update = Channel.query.filter_by(
                    channel_id=req_channel_id
                ).first()

                if channel_to_update:
                    old_priority = channel_to_update.priority
                    channel_to_update.priority = new_priority

                    # Update priorities for channels that will be affected by this change
                    if old_priority > new_priority:
                        # The channel is moving up in the list; decrement priorities in between
                        channels_to_adjust = Channel.query.filter(
                            Channel.priority >= new_priority,
                            Channel.priority < old_priority,
                            Channel.channel_id != req_channel_id,
                        )
                        for channel in channels_to_adjust:
                            channel.priority += 1

                    elif old_priority < new_priority:
                        # The channel is moving down in the list; increment priorities in between
                        channels_to_adjust = Channel.query.filter(
                            Channel.priority <= new_priority,
                            Channel.priority > old_priority,
                            Channel.channel_id != req_channel_id,
                        )
                        for channel in channels_to_adjust:
                            channel.priority -= 1

                    db.session.commit()

            except Exception as e:
                db.session.rollback()  # Rollback in case of any exception
                logger.error(f"Database error: {e}")
                raise e
        print(f"Total time: {time.time() - start_time}")

    def get_channel_by_id(self, ch_id: str) -> Dict:
        """
        Retrieve a channel from the database by its ID.
        Args:
            ch_id (str): The channel ID.
        """

        with self.app.app_context():
            channel = Channel.query.filter_by(channel_id=ch_id).first()
            if channel:
                return channel.to_dict()
            return {}

    def get_channel_by_username(self, ch_username: str) -> Dict:
        """
        Retrieve a channel from the database by its Username.
        Args:
            ch_username (str): The channel username.
        """

        with self.app.app_context():
            channel = Channel.query.filter_by(username=ch_username).first()
            if channel:
                return channel.to_dict()
            return {}

    def remove_channel_by_id(self, ch_id: str) -> None:
        """
        Deactivate a channel by its ID.
        Args:
            ch_id (str): The channel ID.
        """

        with self.app.app_context():
            channel = Channel.query.filter_by(channel_id=ch_id).first()
            if channel:
                channel.active = False
                channel.priority = 9999
                channel.delay_comment = 9999
                db.session.commit()

    def remove_channel_by_username(self, ch_username: str) -> None:
        """
        Deactivate a channel by its username.
        Args:
            ch_username (str): The channel username.
        """
        with self.app.app_context():
            channel = Channel.query.filter_by(username=ch_username).first()
            if channel:
                channel.active = False
                channel.delay_comment = 9999
                db.session.commit()

    def update_channel_photo(self, channel_id: str, photo_url: str) -> None:
        """
        Update the profile picture link of a channel.
        Args:
            channel_id: Channel ID.
            photo_url: New photo URL.
        """
        with self.app.app_context():
            channel = Channel.query.filter_by(channel_id=channel_id).first()
            if channel:
                channel.channel_photo = photo_url
                db.session.commit()

    def get_comments(
        self,
        comment_cols: List[str],
        channel_cols: Optional[List[str]] = None,
        n_recent: int = 50,
        min_likes: int = -1,
        max_likes: int = 999999,
        min_replies: int = -1,
        max_replies: int = 999999,
        channel_id: Optional[str] = None,
        only_null_upload: bool = False,
        only_null_comment_id: bool = False,
        only_null_video_title: bool = False,
        order_by: str = "comment_time",
        join_type: str = "INNER",
    ) -> List[Dict]:
        """
        Get the latest n_recent comments from the comments table.
        """
        with self.app.app_context():
            query = Comment.query

            if channel_id:
                query = query.filter_by(channel_id=channel_id)

            query = query.filter(
                Comment.like_count >= min_likes,
                Comment.reply_count >= min_replies,
                Comment.like_count <= max_likes,
                Comment.reply_count <= max_replies,
            )

            if only_null_upload:
                query = query.filter(
                    (Comment.upload_time == "None") | (Comment.upload_time == "-1")
                )
            if only_null_comment_id:
                query = query.filter(
                    (Comment.comment_id == "None") | (Comment.comment_id == "-1")
                )
            if only_null_video_title:
                query = query.filter(
                    (Comment.video_title == "None") | (Comment.video_title == "-1")
                )

            # If channel_cols is specified, adjust the query to include a join
            if channel_cols:
                # Make sure there's a relationship defined in the Comment model like:
                # channel = db.relationship('Channel', backref='comments')
                query = query.options(joinedload(Comment.channel))

            # Finalize the query with ordering and limit
            query = query.order_by(getattr(Comment, order_by).desc()).limit(n_recent)

            # Execute the query and build the result list
            comments = query.all()
            result = []
            for comment in comments:
                comment_dict = {col: getattr(comment, col) for col in comment_cols}
                if channel_cols and hasattr(comment, "channel"):
                    channel_dict = {
                        col: getattr(comment.channel, col) for col in channel_cols
                    }
                    comment_dict.update(channel_dict)
                result.append(comment_dict)

            return result

    def update_comment(
        self,
        video_link: str,
        comment_id: Optional[str] = None,
        like_cnt: Optional[int] = None,
        reply_cnt: Optional[int] = None,
        upload_time: Optional[str] = None,
        video_title: Optional[str] = None,
        comment_time: Optional[str] = None,
    ) -> None:
        """
        Populate a comment entry with additional information.
        Args:
            video_link:
            comment_id:
            like_cnt:
            reply_cnt:
            upload_time:
            video_title:
            comment_time:
        """
        with self.app.app_context():
            comment = Comment.query.filter_by(video_link=video_link).first()
            if comment:
                # Extract video id from video link
                video_id = video_link.split("v=")[1].split("&")[0]

                if video_id:
                    comment.video_id = video_id

                if comment_id:
                    comment.comment_id = comment_id
                    # Create Comment Link
                    comment.comment_link = (
                        f"https://youtube.com/watch?v={video_id}&lc={comment_id}"
                    )

                if like_cnt is not None:
                    comment.like_count = like_cnt

                if reply_cnt is not None:
                    comment.reply_count = reply_cnt

                if comment_time is not None:
                    comment.comment_time = comment_time

                if upload_time is not None:
                    comment.upload_time = upload_time

                if video_title is not None:
                    comment.video_title = video_title.replace("'", "''")

                db.session.commit()

    def add_comment(
        self,
        ch_id: str,
        video_link: str,
        comment_text: str,
        upload_time: str,
        video_title: str,
    ) -> None:
        """
        Add comment data and update the `last_commented` channel column.
        Args:
            ch_id: Channel ID.
            video_link: Link to the video.
            comment_text: Text of the comment.
            upload_time: Upload time of the video.
            video_title: Title of the video.
        """
        with self.app.app_context():
            datetime_now = datetime.utcnow()
            comment = Comment(  # type: ignore
                channel_id=ch_id,  # type: ignore
                video_link=video_link,  # type: ignore
                comment=comment_text,  # type: ignore
                comment_time=datetime_now,  # type: ignore
                upload_time=datetime.strptime(upload_time, "%Y-%m-%dT%H:%M:%S.%fZ"),  # type: ignore
                video_title=video_title,  # type: ignore
            )  # type: ignore

            try:
                db.session.add(comment)
                # Update Channel's last_commented timestamp
                channel = Channel.query.filter_by(channel_id=ch_id).first()
                if channel:
                    channel.last_commented = datetime_now
                    db.session.commit()
            except Exception as e:
                db.session.rollback()  # Rollback in case of an error
                logger.error(f"Database Error: {e}")
                raise e

    def update_delay_comment(self, channel_id: str, delay: int) -> None:
        """
        Update the delay_comment field for a specific channel.

        Args:
            channel_id (str): The ID of the channel to update.
            delay (int): The new delay value.
        """
        with self.app.app_context():
            channel = Channel.query.filter_by(channel_id=channel_id).first()
            if channel:
                channel.delay_comment = delay
                db.session.commit()
            else:
                raise ValueError(f"Channel with ID {channel_id} not found")

    def update_channel_status(
        self, channel_id: str, new_status: int, delay: int, priority: Union[str, int]
    ) -> None:
        """
        Update the active, delay_comment, and priority fields for a specific channel.

        Args:
            channel_id (str): The ID of the channel to update.
            new_status (int): The new active status.
            delay (int): The new delay_comment value.
            priority (int): The new priority value.
        """
        with self.app.app_context():
            channel = Channel.query.filter_by(channel_id=channel_id).first()
            if channel:
                channel.active = new_status
                channel.delay_comment = delay
                channel.priority = int(priority)
                db.session.commit()
            else:
                raise ValueError(f"Channel with ID {channel_id} not found")

    @staticmethod
    def _row_to_dict(row: Tuple, col_names: List) -> Dict:
        """Transform a table row into a dictionary
        Args:
            row (tuple): The database row
            col_names (list): The names of the columns retrieved
        """

        return dict(zip(col_names, row))
