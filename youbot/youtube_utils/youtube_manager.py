from typing import List, Tuple, Dict, Union, Any
import arrow

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

    def list_channels(self) -> None:
        channels = [(row["channel_id"], row["username"].title(),
                     arrow.get(row["added_on"]).humanize(),
                     arrow.get(row["last_commented"]).humanize())
                    for row in self.db.get_channels()]

        headers = ['Channel Id', 'Channel Name', 'Added On', 'Last Commented']
        self.pretty_print(headers, channels)

    def list_comments(self, n_recent: int = 50, min_likes: int = -1,
                      min_replies: int = -1) -> None:

        comments = [(row["username"].title(), row["comment"],
                     arrow.get(row["comment_time"]).humanize(),
                     row["like_count"], row["reply_count"], row["comment_link"])
                    for row in self.db.get_comments(n_recent, min_likes, min_replies)]

        headers = ['Channel', 'Comment', 'Time', 'Likes', 'Replies', 'Comment URL']
        self.pretty_print(headers, comments)

    @staticmethod
    def pretty_print(headers: List[str], data: List[Tuple]):
        """Print the provided header and data in a visually pleasing manner

        Args:
            headers: The headers to print
            data: The data rows
        """

        print_str = "\n"
        if len(data) == 0:
            return

        separators = []
        for word in headers:
            separators.append('-' * len(word))

        output = [headers, separators] + data

        col_widths = [0] * len(headers)
        for row in output:
            for idx, column in enumerate(row):
                if len(str(column)) > 100:
                    row[idx] = row[idx][:94] + " (...)"
                if len(str(row[idx])) > col_widths[idx]:
                    col_widths[idx] = len(row[idx])

        for row in output:
            for idx, column in enumerate(row):
                column = str(column)
                print_str += "".join(column.ljust(col_widths[idx])) + "  "
            print_str += '\n'
        logger.info(print_str)


class YoutubeManagerError(Exception):
    def __init__(self, message):
        super().__init__(message)
