from typing import *
from datetime import datetime, timedelta
import time
import arrow

from youbot import ColorLogger, YoutubeMySqlDatastore
from .youtube_api import YoutubeApiV3

logger = ColorLogger('YoutubeManager')


class YoutubeManager(YoutubeApiV3):
    __slots__ = ('db', 'sleep_time')

    def __init__(self, config: Dict, db_conf: Dict, sleep_time: int, max_posted_hours: int, tag: str):
        self.db = YoutubeMySqlDatastore(config=db_conf['config'])
        self.sleep_time = sleep_time
        self.max_posted_hours = max_posted_hours
        super().__init__(config, tag)

    def commenter(self):
        # Set sleep_time = 0 for the first loop
        sleep_time = 0
        # Start the main loop
        while True:
            time.sleep(sleep_time)
            channel_ids = [channel['channel_id'] for channel in
                           self.db.get_channels()]
            comments = self.db.get_comments(n_recent=50)
            video_links_commented = [comment['video_link'] for comment in comments]
            latest_videos = self.get_uploads(channels=channel_ids,
                                             max_posted_hours=self.max_posted_hours)
            comments_added = []
            # Sort the videos by the priority of the channels (channel_ids are sorted by priority)
            # and comment in the videos not already commented
            try:
                for video in sorted(latest_videos,
                                    key=lambda _video: channel_ids.index(_video["channel_id"])):
                    video_url = f'https://youtube.com/watch?v={video["id"]}'
                    if video_url not in video_links_commented:
                        comment_text = self.get_next_comment(channel_id=video["channel_id"])
                        # self.comment(video_id=video["id"], comment_text=comment_text)
                        # Add the info of the new comment to be added in the DB
                        comments_added.append((video, video_url, comment_text,
                                               datetime.utcnow().isoformat()))
            except Exception as e:
                logger.error(f"Exception in the main loop of the Commenter:\n{e}")
                sleep_time = self.seconds_until_next_hour()
                logger.error(f"Will sleep until next hour ({sleep_time} seconds)")
            else:
                sleep_time = self.sleep_time
            # Save the new comments added in the DB
            try:
                for (video, video_url, comment_text, comment_time) in comments_added:
                    self.db.add_comment(video["channel_id"], video_link=video_url,
                                        comment_text=comment_text, upload_time=video["published_at"])
            except Exception as e:
                logger.error(f"MySQL error while storing comment:\n{e}")
                raise e
            # REMOVE ME
            break

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

    def refresh_photos(self):
        channel_ids = [channel["channel_id"] for channel in self.db.get_channels()]
        profile_pictures = self.get_profile_pictures(channel_ids)
        for channel_id, picture_url in profile_pictures:
            self.db.update_channel_photo(channel_id, picture_url)

    def set_priority(self, channel_id: str = None, username: str = None, priority: str = None) -> None:
        if channel_id:
            channel_info = self.get_channel_info_by_id(channel_id)
        elif username:
            channel_info = self.get_channel_info_by_username(username)
        else:
            raise YoutubeManagerError("You should either pass channel id or username "
                                      "to add channel!")
        if channel_info:
            self.db.set_priority(channel_data=channel_info, priority=priority)
            logger.info(f"Channel `{channel_info['username']}` priority changed to {priority}!")
        else:
            raise YoutubeManagerError("Channel not found!")

    def list_channels(self) -> None:
        channels = [(row["priority"], row["username"].title(), row["channel_id"],
                     arrow.get(row["added_on"]).humanize(),
                     arrow.get(row["last_commented"]).humanize(),
                     row["channel_photo"]
                     )
                    for row in self.db.get_channels()]

        headers = ['Priority', 'Channel Name', 'Channel ID', 'Added On', 'Last Commented',
                   'Channel Photo']
        self.pretty_print(headers, channels)

    def list_comments(self, n_recent: int = 50, min_likes: int = -1,
                      min_replies: int = -1) -> None:

        comments = [(row["username"].title(), row["comment"],
                     arrow.get(row["comment_time"]).humanize(),
                     row["like_count"], row["reply_count"], row["comment_link"])
                    for row in self.db.get_comments(n_recent, min_likes, min_replies)]

        headers = ['Channel', 'Comment', 'Time', 'Likes', 'Replies', 'Comment URL']
        self.pretty_print(headers, comments)

    def get_next_comment(self, channel_id: str) -> str:
        return f"Test comment for {channel_id}"

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

    @staticmethod
    def seconds_until_next_hour() -> int:
        delta = timedelta(hours=1)
        now = datetime.now()
        next_hour = (now + delta).replace(microsecond=0, second=0, minute=2)
        return (next_hour - now).seconds


class YoutubeManagerError(Exception):
    def __init__(self, message):
        super().__init__(message)
