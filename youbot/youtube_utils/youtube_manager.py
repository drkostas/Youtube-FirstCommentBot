from typing import List, Tuple, Dict, Union, Any
from datetime import datetime, timedelta, timezone

from youbot import ColorizedLogger, YoutubeMySqlDatastore
from .youtube_api import YoutubeApiV3

logger = ColorizedLogger('YoutubeManager')


class YoutubeManager(YoutubeApiV3):
    __slots__ = ('db',)

    def __init__(self, config: Dict, db_conf: Dict, tag: str):
        self.db = YoutubeMySqlDatastore(config=db_conf['config'])
        super().__init__(config, tag)

    def add_channel(self, channel_id: str = None, username: str = None) -> None:
        if channel_id:
            channel_info = self.get_channel_info_by_id(channel_id)
        elif username:
            channel_info = self.get_channel_info_by_username(username)
        else:
            raise YoutubeManagerError("You should either pass channel id or username "
                                      "to add channel!")
        if channel_info:
            self.db.add_channel(channel_data=channel_info)
            logger.info(f"Channel `{channel_info['username']}` successfully added!")
        else:
            raise YoutubeManagerError("Channel not found!")

    def remove_channel(self, channel_id: str = None, username: str = None) -> None:
        if channel_id:
            self.db.remove_channel_by_id(channel_id)
            logger.info(f"Channel `{channel_id}` successfully removed!")
        elif username:
            self.db.remove_channel_by_username(username)
            logger.info(f"Channel `{username}` successfully removed!")
        else:
            raise YoutubeManagerError("You should either pass channel id or username "
                                      "to remove channel!")


class YoutubeManagerError(Exception):
    def __init__(self, message):
        super().__init__(message)
