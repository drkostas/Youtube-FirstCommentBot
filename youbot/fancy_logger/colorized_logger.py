import os
from typing import List, Union
import types
import logging
from termcolor import colored

from .abstract_fancy_logger import AbstractFancyLogger


class ColorizedLogger(AbstractFancyLogger):
    """ColorizedLogger class of the FancyLog package"""

    __slots__ = ('_logger', 'logger_name', '_color', '_on_color', '_attrs',
                 'debug', 'info', 'warn', 'warning', 'error', 'exception', 'critical')

    log_fmt: str = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    log_date_fmt: str = '%Y-%m-%d %H:%M:%S'
    log_level: Union[int, str] = logging.INFO
    _logger: logging.Logger
    log_path: str = None
    logger_name: str
    _color: str
    _on_color: str
    _attrs: List

    def __init__(self, logger_name: str,
                 color: str = 'white', on_color: str = None,
                 attrs: List = None) -> None:
        """
        Args:
            logger_name (str):
            color (str):
            attrs (List): AnyOf('bold', 'dark', 'underline', 'blink', 'reverse', 'concealed')
        """

        self._color = color
        self._on_color = on_color
        self._attrs = attrs if attrs else ['bold']
        self.logger_name = logger_name
        self._logger = self.create_logger(logger_name=logger_name)
        super().__init__()

    def __getattr__(self, name: str):
        """
        Args:
            name (str):
        """

        def log_colored(log_text: str, *args, **kwargs):
            color = self._color if 'color' not in kwargs else kwargs['color']
            on_color = self._on_color if 'on_color' not in kwargs else kwargs['on_color']
            attrs = self._attrs if 'attrs' not in kwargs else kwargs['attrs']
            colored_text = colored(log_text, color=color, on_color=on_color, attrs=attrs)
            return getattr(self._logger, name)(colored_text, *args)

        if name in ['debug', 'info', 'warn', 'warning',
                    'error', 'exception', 'critical']:
            self.add_file_handler_if_needed(self._logger)
            return log_colored
        elif name in ['newline', 'nl']:
            self.add_file_handler_if_needed(self._logger)
            return getattr(self._logger, name)
        else:
            return AbstractFancyLogger.__getattribute__(self, name)

    @staticmethod
    def log_newline(self, num_lines=1):
        # Switch handler, output a blank line
        if hasattr(self, 'main_file_handler') and hasattr(self, 'blank_file_handler'):
            self.removeHandler(self.main_file_handler)
            self.addHandler(self.blank_file_handler)
        self.removeHandler(self.main_streaming_handler)
        self.addHandler(self.blank_streaming_handler)
        # Print the new lines
        for i in range(num_lines):
            self.info('')
        # Switch back
        if hasattr(self, 'main_file_handler') and hasattr(self, 'blank_file_handler'):
            self.removeHandler(self.blank_file_handler)
            self.addHandler(self.main_file_handler)
        self.removeHandler(self.blank_streaming_handler)
        self.addHandler(self.main_streaming_handler)

    def add_file_handler_if_needed(self, logger):
        if not (hasattr(logger, 'main_file_handler') and hasattr(logger, 'blank_file_handler')) \
                and self.log_path:
            # Create a file handler
            self.create_logs_folder(self.log_path)
            main_file_handler = logging.FileHandler(self.log_path)
            main_file_handler.setLevel(self.log_level)
            main_file_handler.setFormatter(logging.Formatter(fmt=self.log_fmt,
                                                             datefmt=self.log_date_fmt))
            # Create a "blank line" file handler
            blank_file_handler = logging.FileHandler(self.log_path)
            blank_file_handler.setLevel(self.log_level)
            blank_file_handler.setFormatter(logging.Formatter(fmt=''))
            # Add file handlers
            logger.addHandler(main_file_handler)
            logger.main_file_handler = main_file_handler
            logger.blank_file_handler = blank_file_handler
        return logger

    def create_logger(self, logger_name: str):
        # Create a logger, with the previously-defined handlers
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.setLevel(self.log_level)
        logger = self.add_file_handler_if_needed(logger)
        # Create a streaming handler
        main_streaming_handler = logging.StreamHandler()
        main_streaming_handler.setLevel(self.log_level)
        main_streaming_handler.setFormatter(logging.Formatter(fmt=self.log_fmt,
                                                              datefmt=self.log_date_fmt))
        # Create a "blank line" streaming handler
        blank_streaming_handler = logging.StreamHandler()
        blank_streaming_handler.setLevel(self.log_level)
        blank_streaming_handler.setFormatter(logging.Formatter(fmt=''))
        # Add streaming handlers
        logger.addHandler(main_streaming_handler)
        logger.propagate = False
        logger.main_streaming_handler = main_streaming_handler
        logger.blank_streaming_handler = blank_streaming_handler
        # Create the new line method
        logger.newline = types.MethodType(self.log_newline, logger)
        logger.nl = logger.newline
        return logger

    @staticmethod
    def create_logs_folder(log_path: str):
        log_path = os.path.abspath(log_path).split(os.sep)
        log_dir = (os.sep.join(log_path[:-1]))
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    @classmethod
    def setup_logger(cls, log_path: str, debug: bool = False, clear_log: bool = False) -> None:
        """ Sets-up the basic_logger

        Args:
            log_path (str): The path where the log file will be saved
            debug (bool): Whether to print debug messages or not
            clear_log (bool): Whether to empty the log file or not
        """
        cls.log_path = os.path.abspath(log_path)
        if clear_log:
            open(cls.log_path, 'w').close()
        cls.log_level = logging.INFO if debug is not True else logging.DEBUG
        fancy_log_logger.info(f"Logger is set. Log file path: {cls.log_path}")


fancy_log_logger = ColorizedLogger(logger_name='FancyLogger', color='white')
