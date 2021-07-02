import traceback
import argparse

from youbot import Configuration, ColorizedLogger, YoutubeManager

logger = ColorizedLogger(logger_name='Main', color='yellow')


def get_args() -> argparse.Namespace:
    """ Setup the argument parser.

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
    required_args.add_argument('-l', '--log', required=True, help="Name of the output log file")
    # Optional args
    optional_args = parser.add_argument_group('Optional Arguments')
    commands = ['commenter', 'accumulator',
                'add_channel', 'remove_channel', 'list_channels', 'list_comments',
                'refresh_photos']
    optional_args.add_argument('-m', '--run-mode', choices=commands,
                               default=commands[0],
                               help='Description of the run modes')
    optional_args.add_argument('-i', '--id', help="The ID of the YouTube Channel")
    optional_args.add_argument('-u', '--username',
                               help="The Username of the YouTube Channel")
    optional_args.add_argument('--n-recent', default=50,
                               help="Number of recent comments to get for `list_comments`")
    optional_args.add_argument('--min_likes', default=-1,
                               help="Number of minimum liked for `list_comments`")
    optional_args.add_argument('--min_replies', default=-1,
                               help="Number of minimum replies for `list_comments`")
    optional_args.add_argument('-d', '--debug', action='store_true',
                               help='Enables the debug log messages')
    optional_args.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    args = parser.parse_args()
    # Custom Condition Checking
    if (args.id is None and args.username is None) and \
            args.run_mode in ['add_channel', 'remove_channel']:
        parser.error('You need to pass either --id or --username when selecting '
                     'the `add_channel` and `remove_channel` actions')
    return args


def commenter(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    raise NotImplementedError()


def accumulator(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    raise NotImplementedError()


def add_channel(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.add_channel(channel_id=args.id, username=args.username)


def remove_channel(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.remove_channel(channel_id=args.id, username=args.username)


def list_channels(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.list_channels()


def list_comments(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    youtube.list_comments(n_recent=args.n_recent, min_likes=args.min_likes,
                          min_replies=args.min_replies)


def refresh_photos(youtube: YoutubeManager, args: argparse.Namespace) -> None:
    raise NotImplementedError()


def main():
    """ This is the main function of main.py

    Example:
        python youbot/main.py -m run_mode_1 -c confs/conf.yml -l logs/output.log
    """

    # Initializing
    args = get_args()
    ColorizedLogger.setup_logger(log_path=args.log, debug=args.debug, clear_log=True)
    # Load the configurations
    conf_obj = Configuration(config_src=args.config_file)
    you_conf = conf_obj.get_config('youtube')[0]
    db_conf = conf_obj.get_config('datastore')[0]
    # Setup Youtube API
    youtube = YoutubeManager(config=you_conf['config'], db_conf=db_conf,
                             tag=conf_obj.tag)
    # Run in the specified run mode
    func = globals()[args.run_mode]
    func(youtube, args)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(str(e) + '\n' + str(traceback.format_exc()))
        raise e
