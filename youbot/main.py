import traceback
import argparse

from youbot import Configuration, ColorizedLogger, \
    DropboxCloudstore, MySqlDatastore, GmailEmailer, YoutubeManagerV3

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
    optional_args.add_argument('-m', '--run-mode', choices=['run_mode_1', 'run_mode_2', 'run_mode_3'],
                               default='run_mode_1',
                               help='Description of the run modes')
    optional_args.add_argument('-d', '--debug', action='store_true',
                               help='Enables the debug log messages')
    optional_args.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser.parse_args()


def main():
    """ This is the main function of main.py

    Example:
        python youbot/main.py -m run_mode_1 -c confs/conf.yml -l logs/output.log
    """

    # Initializing
    args = get_args()
    ColorizedLogger.setup_logger(log_path=args.log, debug=args.debug, clear_log=True)
    # Load the configuration
    conf_obj = Configuration(config_src=args.config_file)
    you_conf = conf_obj.get_config('youtube')[0]
    # Setup Youtube API
    yout_manager = YoutubeManagerV3(config=you_conf['config'],
                                    channel_name=you_conf['channel'],
                                    tag=conf_obj.tag)

    # Test the video retrieval for 3 channels
    pewd_info = yout_manager.get_channel_info_by_username('Pewdiepie')
    v_info = yout_manager.get_channel_info_by_username('Veritasium')
    ku_info = yout_manager.get_channel_info_by_username('Kurzgesagt')
    channel_ids = [pewd_info['id'], v_info['id'], ku_info['id']]
    for video in yout_manager.get_uploads(channels=channel_ids, last_n_hours=12000):
        logger.info(video)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(str(e) + '\n' + str(traceback.format_exc()))
        raise e
