"""Top-level package for YoutubeCommentBot."""

from youbot.fancy_logger import ColorizedLogger
from youbot.configuration import Configuration, validate_json_schema
from youbot.cloudstore import DropboxCloudstore
from youbot.datastore import MySqlDatastore
from youbot.emailer import GmailEmailer

__author__ = "drkostas"
__email__ = "georgiou.kostas94@gmail.com"
__version__ = "2.0"
