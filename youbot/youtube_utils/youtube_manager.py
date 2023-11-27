from typing import *
from datetime import datetime, timedelta
from urllib import response
from dateutil import parser
import time
import arrow
import random
import string
import os
from glob import glob
import requests
import traceback

from youbot import ColorLogger, YoutubeMySqlDatastore, DropboxCloudManager
from .youtube_api import YoutubeApiV3

logger = ColorLogger(logger_name='YoutubeManager', color='cyan')


class YoutubeManager(YoutubeApiV3):
    __slots__ = ('db', 'dbox', 'comments_conf', 'default_sleep_time', 'max_posted_hours', 'api_type',
                 'template_comments', 'log_path', 'upload_logs_every', 'keys_path',
                 'dbox_logs_folder_path', 'dbox_keys_folder_path', 'comments_src',
                 'comment_search_term', 'crashed_file', 'num_comments_to_check', 'base_path')

    def __init__(self, config: Dict, db_conf: Dict, cloud_conf: Dict, comments_conf: Dict,
                 like_bot_conf: Dict,
                 sleep_time: int, fast_sleep_time: int, slow_sleep_time: int,
                 max_posted_hours: int,
                 api_type: str, tag: str, log_path: str, base_path: str):
        global logger
        logger = ColorLogger(
            logger_name=f'[{tag}] YoutubeManager', color='cyan')
        self.base_path = os.path.join(base_path, 'youtube_utils')
        self.db = YoutubeMySqlDatastore(config=db_conf['config'], tag=tag)
        self.comments_conf = None
        if comments_conf is not None:
            self.comments_src = comments_conf['type']
            self.comments_conf = comments_conf['config']
        if like_bot_conf is not None:
            like_bot_conf = like_bot_conf['config']
            self.like_bot_url = like_bot_conf['api_url']
            self.like_bot_key = like_bot_conf['api_key']
            self.like_bot_service = int(like_bot_conf['service'])
            self.like_bot_sleep_time = int(like_bot_conf['sleep_time'])
            self.like_bot_max_mins = int(like_bot_conf['max_minutes_passed'])
        self.dbox = None
        if cloud_conf is not None:
            cloud_conf = cloud_conf['config']
            self.dbox = DropboxCloudManager(config=cloud_conf)
            from dropbox import Dropbox
            self.dbox._handler = Dropbox(app_key=cloud_conf['app_key'],
                                         app_secret=cloud_conf['app_secret'],
                                         oauth2_refresh_token=cloud_conf['refresh_token'])
            self.dbox_logs_folder_path = cloud_conf['logs_folder_path']
            self.dbox_keys_folder_path = cloud_conf['keys_folder_path']
            self.upload_logs_every = int(
                cloud_conf['upload_logs_every']) if 'upload_logs_every' in cloud_conf else 100
        elif self.comments_conf is not None:
            if self.comments_src == 'dropbox':
                raise YoutubeManagerError("Requested `dropbox` comments type "
                                          "but `cloudstore` config is not set!")
        self.default_sleep_time = sleep_time
        self.max_posted_hours = max_posted_hours
        self.api_type = api_type
        self.template_comments = {}
        self.crashed_file = os.path.join(self.base_path, '../../.crashed')
        if self.api_type == 'simulated':
            self.get_uploads = self.simulate_uploads
        elif self.api_type == 'parallel':
            self.get_uploads = super().get_uploads_parallel
            logger.info("Starting in Threading mode.")
        elif self.api_type == 'search':
            self.get_uploads = super().search_uploads
            logger.info("Starting in Search mode.")
        else:  # normal
            self.get_uploads = super().get_uploads
        self.keys_path = config['keys_path']
        self.log_path = log_path
        self.comment_search_term = None
        if 'search_term' in config:
            self.comment_search_term = config['search_term']
        if 'comment_search_term' in config:
            self.comment_search_term = config['comment_search_term']
        if 'load_keys_from_cloud' in config:
            if config['load_keys_from_cloud'] is True:
                self.load_keys_from_cloud()
        super().__init__(config, tag, self.base_path)
        if 'username' in config:
            self.channel_name = config['username']

    def _get_channel_data(self):
        channel_data = list(self.db.get_channels(channel_cols=['channel_id',
                                                               'self_comments_only',
                                                               'delay_comment', 'priority'],
                                                 complex_sort_key=3))
        channel_ids = [channel['channel_id'] for channel in channel_data]
        self_comments_flags_lst = [
            channel['self_comments_only'] for channel in channel_data]
        delay_comment_lst = [channel['delay_comment']
                             for channel in channel_data]
        self_comments_flags = dict(zip(channel_ids, self_comments_flags_lst))
        delay_comment = dict(zip(channel_ids, delay_comment_lst))
        return channel_ids, self_comments_flags, delay_comment

    def commenter(self):
        # Initialize
        sleep_time = 0
        loop_cnt = 0
        errors = 0
        self.load_template_comments()
        channel_ids, self_comments_flags, delay_comment = self._get_channel_data()
        if self.api_type != 'search':
            self.refresh_playlists(channel_ids)
        _, video_links_commented = self.get_comments(channel_ids=channel_ids,
                                                     n_recent=500)
        commented_comments, _ = self.get_comments(channel_ids=channel_ids,
                                                  min_likes=1,
                                                  n_recent=500)
        # Define a different value than sleep_time so it prints the first time
        sleep_time_prev = -1
        logger.info("Done")
        dont_sleep = False
        # Start the main loop
        while True:
            if sleep_time != sleep_time_prev:
                logger.info(f'New sleep time: {sleep_time}')
            sleep_time_prev = sleep_time
            if loop_cnt != 0 and not dont_sleep:
                time.sleep(sleep_time)
                dont_sleep = False
            # Reload stuff and upload logs
            loop_cnt += 1
            if (loop_cnt > self.reload_data_every and sleep_time > self.fast_sleep_time) \
                    or sleep_time > self.slow_sleep_time:
                self.load_template_comments()
                if not self.api_type == 'search':
                    channel_ids, self_comments_flags, delay_comment = self._get_channel_data()
                    self.refresh_playlists(channel_ids)
                # self._apis = self._apis_errored + self._apis  # Retry the failed apis
                # self.self._apis_errored = []
                if self.dbox is not None:
                    self.upload_logs()
                    loop_cnt = 0
            # Load necessary data
            self.load_template_comments()
            channel_ids = [channel['channel_id'] for channel in
                           self.db.get_channels()]
            commented_comments, video_links_commented = self.get_comments(channel_ids=channel_ids,
                                                                          n_recent=500)

            latest_videos = self.get_uploads(channels=channel_ids,
                                             max_posted_hours=self.max_posted_hours)
            comments_added = []
            # Sort the videos by the priority of the channels (channel_ids are sorted by priority)
            # and comment in the videos not already commented
            try:
                loop_start = time.time()
                if self.api_type == 'search':
                    max_posted_hours = sleep_time
                else:
                    max_posted_hours = self.max_posted_hours
                for video in self.get_uploads(channels=channel_ids,
                                              max_posted_hours=max_posted_hours):
                    video_url = f'https://youtube.com/watch?v={video["id"]}'
                    if video_url not in video_links_commented:
                        comment_text = \
                            self.get_next_template_comment(channel_id=video["channel_id"],
                                                           commented_comments=commented_comments,
                                                           self_comments_flags=self_comments_flags)
                        comment_id = self.comment(
                            video_id=video["id"], comment_text=comment_text)
                        if comment_id == '-1':
                            comment_text = '-1'
                        added_comment = True
                        # Add the info of the new comment to be added in the DB after this loop
                        curr_loop_time = time.time() - loop_start
                        if curr_loop_time < delay_comment[video["channel_id"]] - sleep_time \
                           and loop_cnt > 1 and self.api_type != 'search':
                            ch_delay = int(
                                delay_comment[video["channel_id"]] - curr_loop_time - sleep_time)
                            logger.info(
                                f"Requested Delay: {delay_comment[video['channel_id']]}")
                            logger.info(f"Seconds Passed: {curr_loop_time}")
                            logger.info(f"Sleeping for extra: {ch_delay}")
                            time.sleep(ch_delay)
                        video_links_commented.append(video_url)
                        comments_added.append((video, video_url, comment_text,
                                               datetime.utcnow().isoformat(), comment_id))
            except Exception as e:
                if 'SERVICE_UNAVAILABLE' in str(e):
                    logger.warn("YT Service unavailable..")
                elif 'quotaExceeded' in str(e):
                    logger.warn(f"Quota Exceeded..")
                    if len(self._apis) > 1:
                        # Fix by removing the first api
                        self._apis_errored.append(self._apis.pop(0))
                        logger.warn(
                            f'Switching to new API ({len(self._apis)} left)..')
                        errors = 0
                        dont_sleep = True
                    else:
                        dont_sleep = False
                        errors += 1
                elif added_comment is True:  # Raise fatal exception if error after commented
                    self.raise_fatal(e, 'Error after leaving a comment')
                else:
                    error_txt = f"Unknown Exception in the main loop:\n{e}"
                    logger.error(error_txt)
                    errors += 1
                if errors > 5:
                    self._apis = self._apis_errored + self._apis
                    self._apis_errored = []
                    sleep_time = self.seconds_until_next_hour()
                    if sleep_time < 60:
                        sleep_time = 1800
                    logger.info(
                        f"More than 5 errors! Will sleep until {datetime.utcnow() + timedelta(seconds=sleep_time)} ({sleep_time} seconds)")
                    self.upload_logs()
                    loop_cnt = 0
                    errors = 0
            else:
                errors = 0
                if 4 <= datetime.utcnow().hour <= 11:
                    sleep_time = self.slow_sleep_time
                elif datetime.utcnow().minute >= 58 or datetime.utcnow().minute <= 1:
                    sleep_time = self.fast_sleep_time  # check every second when close to new hour
                else:
                    sleep_time = self.default_sleep_time
                if self.exceeds_hot_minute(sleep_time):
                    sleep_time = self.seconds_until_next_hour()
                    if sleep_time < self.fast_sleep_time:
                        sleep_time = self.fast_sleep_time
                    logger.info(
                        f"Will sleep until {datetime.utcnow() + timedelta(seconds=sleep_time)} ({sleep_time} seconds")
            # Save the new comments added in the DB
            try:
                for (video, video_url, comment_text, comment_time, comment_id) in comments_added:
                    self.db.add_comment(video["channel_id"],
                                        video_link=video_url,
                                        comment_text=comment_text,
                                        upload_time=video["published_at"],
                                        video_title=video['title'],
                                        comment_id=comment_id)
                    # Update commented_comments, so we don't have to reload it from the DB
                    commented_comments[video['channel_id']].append({'channel_id': video['channel_id'],
                                                                    'video_link': video_url,
                                                                    'comment': comment_text,
                                                                    'comment_time': comment_time})
                    logger.info(f"Added comment: {video_url}&lc={comment_id}")
            except Exception as e:
                self.raise_fatal(e, 'FatalMySQL error while storing comment')

    def accumulator(self, mode: str = 'id'):
        if mode == 'search':
            logger.info("Starting Accumulator in `search` mode..")
            self._accumulator_search()
        else:
            logger.info("Starting Accumulator in `comment_id` mode..")
            self._accumulator_cid()

    def _accumulator_cid(self):
        # Initialize
        sleep_time = 0
        while True:
            time.sleep(sleep_time)
            updated = 0
            exceptions = []
            try:
                for comment in self.db.get_comments(comment_cols=['video_link'], n_recent=self.num_comments_to_check, only_valid_comment_texts=True):
                    link = comment['video_link']
                    if link is None:
                        continue
                    try:
                        comments = self.get_video_comments(comment_id=c_id)
                        if len(comments) > 0:
                            comment_dict = comments[0]
                        else:
                            continue
                    except Exception as e:
                        exceptions.append(e)
                        continue
                    try:
                        self.db.update_comment(video_link=comment_dict['url'],
                                               comment_id=comment_dict['comment_id'],
                                               like_cnt=comment_dict['like_count'],
                                               reply_cnt=comment_dict['reply_count'],
                                               comment_time=comment_dict['comment_time'])
                        updated += 1
                    except Exception as e:
                        logger.error(f"Exception in update_comment:")
                        logger.error(f"{e}")
                        logger.error(f"{traceback.format_exc()}")
                        continue
            except Exception as e:
                error_txt = f"Exception in the main loop of the Accumulator:\n{e}"
                logger.error(str(error_txt) + '\n' +
                             str(traceback.format_exc()))
                sleep_time = self.seconds_until_next_hour()
                logger.error(
                    f"Will sleep until next hour ({sleep_time} seconds)")
            else:
                if len(exceptions) >= int(self.num_comments_to_check):
                    logger.error(f"Exception in get_video_comments:")
                    logger.error(f"{exceptions[0]}")
                    logger.error(f"{traceback.format_exc()}")
                sleep_time = self.default_sleep_time
                logger.info(
                    f"Updated {updated}/{self.num_comments_to_check} comments.")

    def _accumulator_search(self):
        # Initialize
        sleep_time = 0
        while True:
            time.sleep(sleep_time)
            updated = 0
            exceptions = []
            try:
                for comment in self.db.get_comments(comment_cols=['video_link'], n_recent=self.num_comments_to_check):
                    link = comment['video_link']
                    if link is None:
                        continue
                    try:
                        comments = self.get_video_comments(
                            url=link, search_terms=self.comment_search_term)
                        if len(comments) > 0:
                            comment_dict = comments[0]
                        else:
                            continue
                    except Exception as e:
                        exceptions.append(e)
                        continue
                    try:
                        self.db.update_comment(video_link=comment_dict['url'],
                                               comment_id=comment_dict['comment_id'],
                                               like_cnt=comment_dict['like_count'],
                                               reply_cnt=comment_dict['reply_count'],
                                               comment_time=comment_dict['comment_time'])
                        updated += 1
                    except Exception as e:
                        logger.error(f"Exception in update_comment:")
                        logger.error(f"{e}")
                        logger.error(f"{traceback.format_exc()}")
                        continue
            except Exception as e:
                error_txt = f"Exception in the main loop of the Accumulator:\n{e}"
                logger.error(str(error_txt) + '\n' +
                             str(traceback.format_exc()))
                sleep_time = self.seconds_until_next_hour()
                logger.error(
                    f"Will sleep until next hour ({sleep_time} seconds)")
            else:
                if len(exceptions) >= int(self.num_comments_to_check):
                    logger.error(f"Exception in get_video_comments:")
                    logger.error(f"{exceptions[0]}")
                    logger.error(f"{traceback.format_exc()}")
                sleep_time = self.default_sleep_time
                logger.info(
                    f"Updated {updated}/{self.num_comments_to_check} comments.")

    def like_bot(self):

        req_data = {
            'key': self.like_bot_key,
            'action': 'status',
            'service': self.like_bot_service,
            'order': 349077173
        }

        # req_data = {
        #     'key': self.like_bot_key,
        #     'action': 'add',
        #     'service': self.like_bot_service,
        #     'username': self.channel_name,
        #     'quantity': 100,
        #     'link': 'www.youtube.com/watch?v=OMjvVR14jV0'
        # }
        print(req_data)
        response = requests.post(url=self.like_bot_url,
                                 data=req_data)
        print(response.text)
        return
        while True:
            try:
                for (c_id, url, req_likes) in self.db.get_non_ordered_comments(max_minutes=self.like_bot_max_mins):
                    req_data['quantity'] = req_likes
                    req_data['link'] = f"{url}&lc={c_id}"
                    response = requests.post(url=self.like_bot_url,
                                             data=req_data)

                    response = response.text
                    self.db.update_comment(video_link=url, ordered='1')
                    if 'order' in response:
                        logger.info(
                            f"Ordered {req_data['quantity']} likes for: {req_data['link']}")
                    else:
                        if 'error' in response:
                            err = response.text['error']
                        else:
                            err = "Unknown error in the response."
                        logger.error(
                            f"Like bot returned error for {req_data['link']}: {err}")
                    break
                time.sleep(self.like_bot_sleep_time)
            except Exception as e:
                raise e

    def list_channels(self) -> None:
        channels = [[row["priority"], row["username"].title(), row["channel_id"],
                     arrow.get(row["added_on"]).humanize(),
                     arrow.get(row["last_commented"]).humanize(),
                     row["channel_photo"]
                     ]
                    for row in self.db.get_channels(
            channel_cols=['priority', 'username', 'channel_id', 'added_on', 'last_commented',
                          'delay_comment', 'channel_photo'])]
        headers = ['Priority', 'Channel Name', 'Channel ID', 'Added On', 'Last Commented', 'Delay',
                   'Channel Photo']
        self.pretty_print(headers, channels)

    def list_comments(self, n_recent: int = 50, min_likes: int = -1,
                      min_replies: int = -1, max_likes: int = 99999, max_replies: int = 99999,
                      max_latency: int = 99999) -> None:
        comment_cols = ['comment_time', 'upload_time', 'comment_time', 'like_count',
                        'reply_count', 'comment_link', 'comment']
        channel_cols = ['username']
        comments = []
        for row in self.db.get_comments(comment_cols=comment_cols, channel_cols=channel_cols,
                                        n_recent=n_recent, max_likes=max_likes,
                                        max_replies=max_replies,
                                        min_likes=min_likes, min_replies=min_replies):
            username = row["username"].title()
            comment_time = arrow.get(row["comment_time"]).humanize()
            if row["upload_time"] != "-1" and row["upload_time"] != "None":
                upload_seconds_passed = int(
                    arrow.get(row["upload_time"]).humanize(granularity='second').split(" ")[0])
                comment_seconds_passed = int(
                    arrow.get(row["comment_time"]).humanize(granularity='second').split(" ")[0])
                late = int(upload_seconds_passed - comment_seconds_passed)
            else:
                late = -1
            if late > max_latency:
                continue
            comments.append([username, row["comment"], comment_time,
                             late, row["like_count"], row["reply_count"], row["comment_link"]])

            headers = ['Channel', 'Comment', 'Comment At', 'Latency', 'Likes', 'Replies',
                       'Comment URL']
            self.pretty_print(headers, comments)

    def add_channel(self, channel_id: str = None, username: str = None) -> None:
        if channel_id:
            if channel_id == 'search':
                channel_info = {}
                channel_info['channel_id'] = channel_id
                channel_info['username'] = "Search Results"
                channel_info['added_on'] = datetime.utcnow().isoformat()
                channel_info['last_commented'] = (
                    datetime.utcnow() - timedelta(days=1)).isoformat()
            else:
                channel_info = self.get_channel_info_by_id(channel_id)
        elif username:
            channel_info = self.get_channel_info_by_username(username)
        else:
            raise YoutubeManagerError("You should either pass channel id or username "
                                      "to add channel!")
        if channel_info:
            self.db.add_channel(channel_data=channel_info, active=active)
            logger.info(
                f"Channel `{channel_info['username']}` successfully added!")
        else:
            raise YoutubeManagerError("Channel not found!")

    def add_channels(self, ids_file: str):
        current_channel_ids = [row['channel_id'] for row in self.db.get_channels(
            channel_cols=['channel_id', 'username'], where='active=True')]
        print(current_channel_ids)

        with open(ids_file, 'r') as f:
            ids = f.readlines()

        for ch_id in ids:
            ch_id = ch_id.replace('\n', '').strip()
            if ch_id not in current_channel_ids:
                self.add_channel(channel_id=ch_id)

    def update_likes(self, channels_file: str):
        with open(channels_file, 'r') as f:
            channels_and_likes = f.readlines()

        for ch_and_like in channels_and_likes:
            ch_id, likes = ch_and_like.replace('\n', '').strip().split(',')
            try:
                self.add_channel(channel_id=ch_id)
            except Exception as e:
                pass
            self.db.set_likes(channel_id=ch_id, likes=likes)

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
        channel_ids = [channel["channel_id"]
                       for channel in self.db.get_channels(channel_cols=['channel_id'], where='TRUE')]
        try:
            profile_pictures = self.get_profile_pictures(channel_ids)
        except Exception as e:
            logger.error("One of the channels failed. Trying one by one.")
            profile_pictures = []
            for channel_id in channel_ids:
                try:
                    profile_picture = self.get_profile_pictures([channel_id])[
                        0]
                    profile_pictures.append(profile_picture)
                except Exception as e:
                    logger.error(
                        f"Channel id: {channel_id} failed. Putting YT picture instead.")
                    profile_picture = self.get_profile_pictures(
                        ['UCBR8-60-B28hp2BmDPdntcQ'])[0]
                    profile_pictures.append(profile_picture)
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
            logger.info(
                f"Channel `{channel_info['username']}` priority changed to {priority}!")
        else:
            raise YoutubeManagerError("Channel not found!")

    def fill_upload_times(self, n_recent, min_likes, min_replies):
        video_ids = [row['video_link'].split("?v=")[-1]
                     for row in self.db.get_comments(comment_cols=['video_link'],
                                                     n_recent=n_recent,
                                                     min_likes=min_likes,
                                                     min_replies=min_replies,
                                                     only_null_upload=True)]
        for video in self.get_video_info(videos=video_ids):
            video_link = f"https://youtube.com/watch?v={video['video_id']}"
            self.db.update_comment(video_link=video_link,
                                   upload_time=video['upload_time'])

    def fix_comment_links(self, n_recent, min_likes, min_replies):
        video_info = [
            (row['video_link'].split("?v=")[-1], row['comment_id'])
            for row in self.db.get_comments(comment_cols=['video_link', 'comment_id'],
                                            n_recent=n_recent,
                                            min_likes=min_likes, min_replies=min_replies)]
        for video_id, comment_id in video_info:
            video_link = f"https://youtube.com/watch?v={video_id}"
            self.db.update_comment(video_link=video_link,
                                   comment_id=comment_id)

    def fill_video_titles(self, n_recent, min_likes, min_replies):
        video_ids = [row['video_link'].split("?v=")[-1]
                     for row in self.db.get_comments(comment_cols=['video_link'],
                                                     n_recent=n_recent,
                                                     min_likes=min_likes, min_replies=min_replies,
                                                     only_null_video_title=True)]
        for video in self.get_video_info(videos=video_ids):
            video_link = f"https://youtube.com/watch?v={video['video_id']}"
            self.db.update_comment(video_link=video_link,
                                   video_title=video['video_title'])

    def retrieve_old_channels(self, n_recent, min_likes, min_replies):
        commented_channel_ids = [comment["channel_id"]
                                 for comment in self.db.get_comments(comment_cols=['channel_id'],
                                                                     n_recent=n_recent,
                                                                     min_likes=min_likes,
                                                                     min_replies=min_replies)]
        current_channel_ids = [channel["channel_id"]
                               for channel in self.db.get_channels(channel_cols=['channel_id'],
                                                                   where='TRUE')]
        for channel_id in set(commented_channel_ids):
            if channel_id not in current_channel_ids:
                self.add_channel(channel_id=channel_id, active=False)

    def get_comments(self, n_recent, channel_ids=None, min_likes: int = -1):
        comment_cols = ['channel_id', 'video_link', 'comment', 'comment_time']
        commented_comments = {}
        video_links_commented = []
        if channel_ids is None:
            commented_comments[None] = list(self.db.get_comments(comment_cols=comment_cols,
                                                                 channel_id=None,
                                                                 n_recent=n_recent,
                                                                 min_likes=min_likes))
            video_links_commented += [comment['video_link'] for comment in
                                      commented_comments[None]]
        else:
            for channel_id in channel_ids:
                commented_comments[channel_id] = list(self.db.get_comments(comment_cols=comment_cols,
                                                                           channel_id=channel_id,
                                                                           n_recent=n_recent,
                                                                           min_likes=min_likes))
                video_links_commented += [comment['video_link'] for comment in
                                          commented_comments[channel_id]]
        return commented_comments, video_links_commented

    def load_template_comments(self):
        if self.comments_conf is None:
            raise YoutubeManagerError("Tried to load template comments "
                                      "but `comments` is not set in the config!")
        # Download files from dropbox
        if self.comments_src == 'dropbox':
            # TODO: implement this in the dropbox lib
            if not os.path.exists(self.comments_conf["local_folder_name"]):
                os.makedirs(self.comments_conf["local_folder_name"])
            for file in self.dbox.ls(self.comments_conf['dropbox_folder_name']).keys():
                if file[-4:] == '.txt':
                    self.dbox.download_file(f'{self.comments_conf["dropbox_folder_name"]}/{file}',
                                            f'{self.comments_conf["local_folder_name"]}/{file}')
        # Load comments from files
        if self.comments_src in ('local', 'dropbox'):
            comments_path = os.path.join(self.base_path, '../..', self.comments_conf['local_folder_name'],
                                         "*.txt")
            for file in glob(comments_path):
                file_name = file.split('/')[-1][:-4]
                with open(file) as f:
                    self.template_comments[file_name] = [
                        _f.rstrip() for _f in f.readlines()]

    def get_next_template_comment(self, channel_id: str, commented_comments: Dict) -> str:
        """ TODO: Probably much more efficient with numpy or sql. """
        commented_comments = commented_comments[channel_id]
        available_comments = self.template_comments['default'].copy()
        # Build the comments pool
        if channel_id in self.template_comments:
            if self_comments_flags == 1:
                available_comments = self.template_comments[channel_id]
            else:
                available_comments = self.template_comments[channel_id] + \
                    available_comments
        # Extract unique comments commented
        unique_com_coms = set(data['comment'] for data in commented_comments)
        new_comments = set(available_comments) - unique_com_coms
        if new_comments:  # If we have new template comments
            comment = next(iter(new_comments))
        else:  # Otherwise, pick the oldest one (with duplicate handling
            comment_dates = {}
            for unique_comment in unique_com_coms:
                comment_dates[unique_comment] = parser.parse(
                    '1994-04-30T08:00:00.000000')
                for com_data in commented_comments:
                    if com_data['comment'] == unique_comment:
                        comment_time = parser.parse(com_data['comment_time'])
                        if comment_time > comment_dates[unique_comment]:
                            comment_dates[unique_comment] = parser.parse(
                                com_data['comment_time'])
            comment = [k for k, v in sorted(comment_dates.items(),
                                            key=lambda p: p[1], reverse=False)][0]

        return comment

    def upload_logs(self):
        log_name = self.log_path.split(os.sep)[-1][:-4]
        day = datetime.today().day
        log_name += f'_day{day}.txt'
        upload_path = os.path.join(self.dbox_logs_folder_path, log_name)
        with open(self.log_path, 'rb') as f:
            file_to_upload = f.read()
        self.dbox.upload_file(file_bytes=file_to_upload,
                              upload_path=upload_path)

    def load_keys_from_cloud(self):
        if self.dbox is None:
            raise YoutubeManagerError("`load_keys_from_cloud` was set to True "
                                      "but no `cloudstore` config was given!")

        if not os.path.exists(self.keys_path):
            os.makedirs(self.keys_path)
        for file in self.dbox.ls(self.dbox_keys_folder_path).keys():
            if file[-5:] == '.json':
                self.dbox.download_file(f'{self.dbox_keys_folder_path}/{file}',
                                        f'{self.keys_path}/{file}')

    def simulate_uploads(self, channels: List, max_posted_hours: int = 2) -> Dict:
        """ Generates new uploads for the specified channels.

        Args:
            channels(list): A list with channel IDs
            max_posted_hours:
        """
        num_videos = random.randint(1, 4)
        channels = [(channel['username'], channel['channel_id']) for channel in
                    self.db.get_channels()]
        for video_ind in range(num_videos):
            vid_id = ''.join(
                random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=11))
            title_length = random.randint(10, 40)
            vid_title = ''.join(random.choices(
                string.ascii_lowercase + ' ', k=title_length)).title()
            ch_name, ch_id = random.choice(channels)
            channels.remove((ch_name, ch_id))
            secs = random.randint(1, 59)
            mins = random.randint(1, 59)
            hours = random.randint(1, 59)
            published_at = (datetime.utcnow() - timedelta(seconds=secs,
                                                          minutes=mins,
                                                          hours=hours)).isoformat()
            upload = {'id': vid_id,
                      'published_at': published_at,
                      'title': vid_title,
                      'channel_title': ch_name,
                      'channel_id': ch_id}
            yield upload

    @staticmethod
    def pretty_print(headers: List[str], data: List[List]):
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
        hot_minute_start = 1
        hot_minute_end = 58
        now = datetime.utcnow()
        now_minute = now.minute
        if now_minute <= hot_minute_start or now_minute >= hot_minute_end:
            minute = now_minute+1
            delta = timedelta(hours=0)
        else:
            minute = hot_minute_end
            delta = timedelta(hours=0)
        if minute > 59:
            minute = 0
            delta = timedelta(hours=1)
        target_time = (now + delta).replace(microsecond=0,
                                            second=0, minute=minute)
        return (target_time - now).seconds

    @staticmethod
    def exceeds_hot_minute(seconds) -> bool:
        hot_minute_end = 58
        now = datetime.utcnow()
        now_minute = now.minute + seconds/60
        flag = now_minute >= hot_minute_end
        return flag

    @staticmethod
    def touch(fname, mode=0o666, dir_fd=None, **kwargs):
        flags = os.O_CREAT | os.O_APPEND
        with os.fdopen(os.open(fname, flags=flags, mode=mode, dir_fd=dir_fd)) as f:
            os.utime(f.fileno() if os.utime in os.supports_fd else fname,
                     dir_fd=None if os.supports_fd else dir_fd, **kwargs)


class YoutubeManagerError(Exception):
    def __init__(self, message):
        super().__init__(message)
