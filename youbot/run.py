import traceback
import argparse
import os

from youbot import Configuration, ColorLogger, YoutubeManager

logger = ColorLogger(logger_name='Main', color='yellow')


def get_args() -> argparse.Namespace:
    """ Set up the argument parser.

    Returns:
        argparse.Namespace:
    """

    parser = argparse.ArgumentParser(
        description='A template for python projects.',
        add_help=False)
    # Required Args
    required_args = parser.add_argument_group('Required Arguments')
    config_file_params = {
        'type': argparse.FileType('r'),
        'required': True,
        'help': "The configuration yml file"
    }
    required_args.add_argument('-c', '--config-file', **config_file_params)
    required_args.add_argument(
        '-l', '--log', required=True, help="Name of the output log file")
    # Optional args
    optional_args = parser.add_argument_group('Optional Arguments')
    commands = ['commenter', 'accumulator', 'like_bot',
                'add_channel', 'add_channels', 'remove_channel', 'list_channels', 'list_comments',
                'refresh_photos', 'set_priority', 'update_likes',
                'fill_upload_times', 'fill_video_titles', 'fix_comment_links',
                'retrieve_old_channels']
    optional_args.add_argument('-m', '--run-mode', choices=commands,
                               default=commands[0],
                               help='Description of the run modes')
    optional_args.add_argument(
        '-i', '--id', help="The ID of the YouTube Channel")
    optional_args.add_argument('-u', '--username',
                               help="The Username of the YouTube Channel")
    optional_args.add_argument('--acc_mode', default='id',
                               help="The mode of the accumulator (id or search).")
    optional_args.add_argument('--channel_ids_file',
                               help="A file with a list of YouTube urls")
    optional_args.add_argument('--n-recent', default=50,
                               help="Number of recent comments to get for `list_comments`")
    optional_args.add_argument('--min_likes', default=-1,
                               help="Number of minimum liked for `list_comments`")
    optional_args.add_argument('--min_replies', default=-1,
                               help="Number of minimum replies for `list_comments`")
    optional_args.add_argument('--priority',
                               help="Priority number for specified channel for `set_priority`")
    optional_args.add_argument('-d', '--debug', action='store_true',
                               help='Enables the debug log messages')
    optional_args.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit")

    args = parser.parse_args()
    # Custom Condition Checking
    if (args.id is None and args.username is None) and \
            args.run_mode in ['add_channel', 'remove_channel', 'set_priority']:
        parser.error('You need to pass either --id or --username when selecting '
                     'the `add_channel`, `remove_channel`, or `set_priority` actions')
    if (args.priority is None) and \
            args.run_mode in ['set_priority']:
        parser.error('You need to pass --priority when selecting '
                     'the `set_priority` action')
    return args


def commenter(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.commenter()


def accumulator(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.accumulator(mode=args.acc_mode)


def like_bot(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.like_bot()


def set_priority(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.set_priority(channel_id=args.id, username=args.username,
                         priority=args.priority)


def add_channel(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.add_channel(channel_id=args.id, username=args.username)


def add_channels(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.add_channels(ids_file=args.channel_ids_file)


def remove_channel(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.remove_channel(channel_id=args.id, username=args.username)


def list_channels(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.list_channels()


def list_comments(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.list_comments(n_recent=args.n_recent, min_likes=args.min_likes,
                          min_replies=args.min_replies)


def update_likes(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.update_likes(channels_file=args.channel_ids_file)


def refresh_photos(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.refresh_photos()


def fill_upload_times(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.fill_upload_times(args.n_recent, args.min_likes, args.min_replies)


def fill_video_titles(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.fill_video_titles(args.n_recent, args.min_likes, args.min_replies)


def fix_comment_links(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.fix_comment_links(args.n_recent, args.min_likes, args.min_replies)


def retrieve_old_channels(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.retrieve_old_channels(
        args.n_recent, args.min_likes, args.min_replies)


def main():
    """ This is the main function of run.py

    Example:
        python youbot/run.py -m commenter -c confs/commenter.yml -l logs/commenter.log
    """
    global logger

    # Initializing
    args = get_args()
    ColorLogger.setup_logger(
        log_path=args.log, debug=args.debug, clear_log=False)
    # Load configurations
    conf_obj = Configuration(config_src=args.config_file)
    tag = conf_obj.tag
    # Reconfigures it with the tag
    logger = ColorLogger(logger_name=f'[{tag}] Main', color='yellow')
    you_conf = conf_obj.get_config('youtube')[0]
    sleep_time = int(you_conf['config']['sleep_time']) \
        if 'sleep_time' in you_conf['config'] else 120
    max_posted_hours = int(you_conf['config']['max_posted_hours']) \
        if 'max_posted_hours' in you_conf['config'] else 24
    db_conf = conf_obj.get_config('datastore')[0]
    comments_conf = None
    if 'comments' in conf_obj.config:  # Optional
        comments_conf = conf_obj.get_config('comments')[0]
    cloud_conf = None
    if 'cloudstore' in conf_obj.config:  # Optional
        cloud_conf = conf_obj.get_config('cloudstore')[0]
    like_bot_conf = None
    if 'like_bot' in conf_obj.config:  # Optional
        like_bot_conf = conf_obj.get_config('like_bot')[0]
    emailer_conf = None
    if 'emailer' in conf_obj.config:  # Not implemented yet
        emailer_conf = conf_obj.get_config('emailer')[0]
    # Setup YouTube API
    youtube = YoutubeManager(config=you_conf['config'],
                             db_conf=db_conf, cloud_conf=cloud_conf,
                             comments_conf=comments_conf,
                             like_bot_conf=like_bot_conf,
                             sleep_time=sleep_time,
                             max_posted_hours=max_posted_hours,
                             api_type=you_conf['type'], tag=conf_obj.tag, log_path=args.log,
                             base_path=os.path.dirname(os.path.abspath(__file__)))
    # Run in the specified run mode
    func = globals()[args.run_mode]
    func(youtube, args)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(str(e) + '\n' + str(traceback.format_exc()))
        raise e
