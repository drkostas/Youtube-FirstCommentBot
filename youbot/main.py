import traceback
import argparse

from youbot import Configuration, ColorizedLogger, timeit, profileit, \
    DropboxCloudstore, MySqlDatastore, GmailEmailer

basic_logger = ColorizedLogger(logger_name='Main', color='yellow')
fancy_logger = ColorizedLogger(logger_name='FancyMain',
                               color='blue',
                               on_color='on_red',
                               attrs=['underline', 'reverse', 'bold'])


def get_args() -> argparse.Namespace:
    """Setup the argument parser

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


@timeit(custom_print="{func_name} took {duration:2.5f} sec(s) to run!")
def main():
    """This is the main function of main.py

    Example:
        python youbot/main.py -m run_mode_1
                                                     -c confs/template_conf.yml
                                                     -l logs/output.log
    """

    # Initializing
    args = get_args()
    ColorizedLogger.setup_logger(log_path=args.log, debug=args.debug, clear_log=True)
    # Load the configuration
    # configuration = Configuration(config_src=args.config_file,
    #                               config_schema_path='yml_schema_strict.json')
    configuration = Configuration(config_src=args.config_file)
    # Prints
    basic_logger.info("Starting in run mode: {0}".format(args.run_mode))
    basic_logger.info("Examples:")
    fancy_logger.info("You can customize the logger like this")
    fancy_logger.info("You can customize each log message differently",
                      color="green", on_color="on_white", attrs=[])
    basic_logger.info("If you want to print complete blank lines use nl(num_lines=<#>):")
    basic_logger.nl(num_lines=2)
    # Example timeit code block
    basic_logger.info("You can use timeit either as a function Wrapper or a ContextManager:")
    for i in range(5):
        custom_print = f"{i}: " + "Iterating in a 10,000-number-range took {duration:2.5f} seconds."
        skip = i in [1, 2, 3]
        with timeit(custom_print=custom_print, skip=skip):
            for _ in range(10000):
                pass
    # Example profileit code block
    basic_logger.info(
        "Lastly, you can use profileit either as a function Wrapper or a ContextManager:")
    with profileit():
        # CloudStore
        cloud_conf = configuration.get_config('cloudstore')[0]
        if cloud_conf['type'] == 'dropbox' and cloud_conf['config']['api_key'] != 'DROPBOX_API_KEY':
            dropbox_obj = DropboxCloudstore(config=cloud_conf['config'])
            basic_logger.info(f"Base folder contents in dropbox:\n{dropbox_obj.ls().keys()}")
        # MySqlDatastore
        cloud_conf = configuration.get_config('datastore')[0]
        if cloud_conf['type'] == 'mysql' and cloud_conf['config']['username'] != 'MYSQL_USERNAME':
            mysql_obj = MySqlDatastore(config=cloud_conf['config'])
            basic_logger.info(f"List of tables in DB:\n{mysql_obj.show_tables()}")
        # GmailEmailer
        cloud_conf = configuration.get_config('emailer')[0]
        if cloud_conf['type'] == 'gmail' and cloud_conf['config']['api_key'] != 'GMAIL_API_KEY':
            basic_logger.info(f"Sending Sample Email to the email address set..")
            gmail_obj = GmailEmailer(config=cloud_conf['config'])
            gmail_obj.send_email(subject='starter',
                                 to=[gmail_obj.email_address],
                                 text='GmailEmailer works!')
            basic_logger.info(f"Done!")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        basic_logger.error(str(e) + '\n' + str(traceback.format_exc()))
        raise e
