from typing import List, Tuple, Dict, Union, Any
from abc import ABC, abstractmethod
import os
import re
import math
from datetime import datetime, timedelta, timezone
import dateutil.parser
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow
from oauth2client.client import OAuth2WebServerFlow
import googleapiclient
from googleapiclient.discovery import build
import httplib2
from threading import Thread
import time
from itertools import islice, cycle
import traceback
from youbot import ColorLogger

logger = ColorLogger(logger_name='YoutubeApi', color='green')


class AbstractYoutubeApi(ABC):
    __slots__ = ('channel_name', 'channel_id', '_apis', 'tag', 'playlist_ids')

    @abstractmethod
    def __init__(self, config: Dict, tag: str) -> None:
        """
        The basic constructor. Creates a new instance of YoutubeManager using the specified credentials

        :param config:
        """

        self.channel_playlists = None
        self.tag = tag
        self._apis = []
        for cr_ind, creds in enumerate(config['credentials']):
            _api = self._build_api(
                client_id=creds['client_id'],
                client_secret=creds['client_secret'],
                api_version=config['api_version'],
                read_only_scope=config['read_only_scope'],
                tag=f'{self.tag}_{cr_ind}')
            self._apis.append(_api)
        self.channel_name, self.channel_id = self._get_my_username_and_id()

    @staticmethod
    @abstractmethod
    def _build_api(*args, **kwargs):
        pass

    @abstractmethod
    def _get_my_username_and_id(self) -> str:
        pass


class YoutubeApiV3(AbstractYoutubeApi):

    def __init__(self, config: Dict, tag: str):
        global logger
        logger = ColorLogger(logger_name=f'[{tag}] YoutubeApi', color='green')
        self.parallel_uploads = ParallelUploads()
        super().__init__(config, tag)

    @staticmethod
    def _build_api(client_id: str, client_secret: str, api_version: str, read_only_scope: str,
                   tag: str) -> googleapiclient.discovery.Resource:
        """
        Build a YouTube api connection.

        Args:
            client_id:
            client_secret:
            api_version:
            read_only_scope:
            tag:
        """

        flow = OAuth2WebServerFlow(client_id=client_id,
                                   client_secret=client_secret,
                                   redirect_uri='http://localhost',  # Add this to GCloud(web oath)
                                   scope=read_only_scope)
        base_path = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(base_path, '../../', 'keys', f'{tag}.json')
        storage = Storage(key_path)
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            args = []  # ['--noauth_local_webserver']
            flags = argparser.parse_args(args=args)
            credentials = run_flow(flow, storage, flags)

        api = build('youtube', api_version, http=credentials.authorize(httplib2.Http()))
        return api

    def _get_my_username_and_id(self) -> Tuple[str, str]:
        channels_response = self._apis[0].channels().list(
            part="snippet",
            fields='items(id,snippet(title))',
            mine='true'
        ).execute()
        if channels_response:
            channel_info = self._yt_to_channel_dict(channels_response)
            my_username = channel_info['username']
            my_id = channel_info['channel_id']
        else:
            error_msg = "Got empty response when trying to get the self username."
            logger.error(error_msg)
            raise Exception(error_msg)
        return my_username, my_id

    def comment(self, video_id: str, comment_text: str) -> None:

        try:
            properties = {'snippet.channelId': self.channel_id,
                          'snippet.videoId': video_id,
                          'snippet.topLevelComment.snippet.textOriginal': comment_text}
            self._comment_threads_insert(properties=properties,
                                         part='snippet')
        except Exception as exc:
            logger.error(f"An error occurred:\n{exc}")

    def get_channel_info_by_username(self, username: str) -> Union[Dict, None]:
        """ Queries YouTube for a channel using the specified username.

        Args:
            username (str): The username to search for
        """

        channels_response = self._apis[0].channels().list(
            forUsername=username,
            part="snippet",
            fields='items(id,snippet(title))'
        ).execute()
        if channels_response:
            channel = self._yt_to_channel_dict(channels_response)
            if channel is not None:
                channel['username'] = username
        else:
            logger.warn(f"Got empty response for channel username: {username}")
            channel = {}
        return channel

    def get_channel_info_by_id(self, channel_id: str) -> Union[Dict, None]:
        """ Queries YouTube for a channel using the specified channel id.

        Args:
            channel_id (str): The channel ID to search for
        """

        channels_response = self._apis[0].channels().list(
            id=channel_id,
            part="snippet",
            fields='items(id,snippet(title))'
        ).execute()

        return self._yt_to_channel_dict(channels_response)

    def get_uploads_parallel(self, channels: List, max_posted_hours: int = 2) -> Dict:

        max_channels = 50
        # Refresh playlists if needed
        if self.channel_playlists is None:
            self.refresh_playlists(channels)
        if len(channels) <= max_channels:
            for upload in self._get_uploads(api=self._apis[0],
                                            channels=channels,
                                            max_posted_hours=max_posted_hours):
                yield upload
        else:
            self.parallel_uploads.uploads = []
            self.parallel_uploads.done = 0
            # smart way of keeping the ordering (mostly)
            # assuming two splits
            # TODO: implement for more than 2 - general case
            channels = channels[::2] + channels[1::2]
            channels_lists = self.split_list(channels, max_channels)
            if len(self._apis) < len(channels_lists):
                apis = list(islice(cycle(self._apis), len(channels_lists)))
            else:
                apis = self._apis
            threads = []
            for channels, api in zip(channels_lists, apis):
                t = Thread(target=self.parallel_uploads.get, args=(channels, api, max_posted_hours,
                                                                   self._get_uploads))
                t.start()
                threads.append(t)
            start_t = time.time()
            while self.parallel_uploads.done < len(channels_lists) and time.time() - start_t < 30:
                if len(self.parallel_uploads.uploads) > 0:
                    yield self.parallel_uploads.uploads.pop()
            for t in threads:
                t.join()

    def get_uploads(self, channels: List, max_posted_hours: int = 2) -> Dict:
        max_channels = 50
        # Refresh playlists if needed
        if self.channel_playlists is None:
            self.refresh_playlists(channels)
        if len(channels) <= max_channels:
            for upload in self._get_uploads(api=self._apis[0],
                                            channels=channels,
                                            max_posted_hours=max_posted_hours):
                yield upload
        else:
            channels_lists = self.split_list(channels, max_channels)
            if len(self._apis) < len(channels_lists):
                apis = list(islice(cycle(self._apis), len(channels_lists)))
            else:
                apis = self._apis
            for channels, api in zip(channels_lists, apis):
                for upload in self._get_uploads(api=api,
                                                channels=channels,
                                                max_posted_hours=max_posted_hours):
                    yield upload

    def _get_uploads(self, api, channels: List, max_posted_hours: int = 2) -> Dict:
        """ Retrieves new uploads for the specified channels.

        Args:
            channels(list): A list with channel IDs
            max_posted_hours:
        """

        def iter_uploads(channels, channel_playlists, _api, _max_posted_hours):
            # TODO: maybe pop the playlists yielded for error handling?
            for ch_id in channels:
                if ch_id not in channel_playlists:
                    continue
                playlist = channel_playlists[ch_id]
                playlist_id = playlist["contentDetails"]["relatedPlaylists"]["uploads"]
                for _upload in self._get_uploads_playlist(_api, ch_id, playlist_id, _max_posted_hours):
                    if _upload is None:
                        continue
                    try:
                        _upload['channel_title'] = playlist['snippet']['title']
                        _upload['channel_id'] = playlist['id']
                        yield _upload
                    except Exception as e:
                        logger.error(f"playlist_id: {e} not found")

        # Separate the channels list in 50-sized channel lists
        # channels_lists = self.split_list(channels, 50)  # Redundant
        # For each playlist ID, get 50 videos
        try:
            for upload in iter_uploads(channels, self.channel_playlists, api, max_posted_hours):
                yield upload
        except Exception as e:
            logger.warn(e)
            logger.warn("Refreshing Playlists and retrying..")
            self.refresh_playlists(channels)
            for upload in iter_uploads(channels, self.channel_playlists, api, max_posted_hours):
                yield upload

    def refresh_playlists(self, channels_lists):
        playlist_ids_lst = []
        if len(channels_lists) > 50:
            channels_lists = self.split_list(channels_lists, 50)
        else:
            channels_lists = [channels_lists]
        for channels in channels_lists:
            try:
                channels_response = self._apis[0].channels().list(
                    id=",".join(channels),
                    part="contentDetails,snippet",
                    fields="items(id,contentDetails(relatedPlaylists(uploads)),snippet(title))"
                ).execute()

                if "items" not in channels_response:
                    logger. error(
                        f"Got empty response for channels {channels} when trying to refresh playlists."
                    )
                    continue
                for item in channels_response["items"]:
                    if item["snippet"]["title"] != "":
                        playlist_ids_lst.append(item)
            except Exception as e:
                logger.error("Error refreshing some playlists..")
                logger.error(f"{str(e)} : {traceback.format_exc()}")
                continue
        self.channel_playlists = {playlist['id']: playlist for playlist in playlist_ids_lst}

    def get_video_comments(self, url: str, search_terms: str = None) -> List:
        """ Populates a list with comments (and their replies).

        Args:
            url:
            search_terms:
        """
        # TODO: Make it more efficient by checking 50 comments at a time
        if not search_terms:
            search_terms = self.channel_name
        video_id = re.search(r"^.*(youtu\.be\/|vi?\/|u\/\w\/|embed\/|\?vi?=|\&vi?=)([^#\&\?]*).*",
                             url).group(2)
        page_token = ""  # "&pageToken={}".format(page_token)
        comment_threads_response = self._apis[0].commentThreads().list(
            part="snippet",
            maxResults=100,
            videoId="{}{}".format(video_id, page_token),
            searchTerms=search_terms
        ).execute()

        comments = []
        for comment_thread in comment_threads_response['items']:
            try:
                channel_name = comment_thread['snippet']['topLevelComment']['snippet'][
                    'authorDisplayName']
                if channel_name == self.channel_name:
                    current_comment = {"url": url, "video_id": video_id,
                                       "comment_id": comment_thread['id'],
                                       "like_count":
                                           comment_thread['snippet']['topLevelComment']['snippet'][
                                               'likeCount'],
                                       "reply_count": comment_thread['snippet']['totalReplyCount'],
                                       "comment_time":
                                           comment_thread['snippet']['topLevelComment']['snippet'][
                                               'publishedAt']}
                    comments.append(current_comment)
            except Exception as e:
                logger.error(f"Exception in get_video_comments() for {comment_thread}.")
                logger.error(f"{e}")

        return comments

    def get_profile_pictures(self, channels: List = None) -> List[Tuple[str, str]]:
        """ Gets the profile picture urls for a list of channel ids (or for the self channel).

        Args:
            channels:

        Returns:
            profile_pictures: [(channel_id, thumbnail_url), ..]
        """

        if channels is None:
            profile_pictures_requests = [self._apis[0].channels().list(
                mine="true",
                part="snippet",
                fields='items(id,snippet(thumbnails(default)))'
            )]
        else:
            channels_list = self.split_list(channels, 50)
            profile_pictures_requests = []
            for channels in channels_list:
                profile_pictures_requests.append(self._apis[0].channels().list(
                    id=",".join(channels),
                    part="snippet",
                    fields='items(id,snippet(thumbnails(default)))'
                ))

        profile_pictures_responses = []
        for profile_pictures_request in profile_pictures_requests:
            profile_pictures_response = profile_pictures_request.execute()
            profile_pictures_responses.append(profile_pictures_response)

        profile_pictures_result = []
        for profile_pictures_response in profile_pictures_responses:
            for profile_picture in profile_pictures_response["items"]:
                profile_pictures_result.append(
                    (profile_picture["id"],
                     profile_picture["snippet"]["thumbnails"]["default"]["url"]))

        return profile_pictures_result

    def get_video_info(self, videos: List):
        videos_lists = self.split_list(videos, 50)
        videos_found = []
        # Get the Playlist IDs of each channel
        for videos in videos_lists:
            channels_response = self._apis[0].videos().list(
                id=",".join(videos),
                part="contentDetails,snippet",
                fields="items(id,snippet(channelId,publishedAt,title))"
            ).execute()
            videos_found.extend(channels_response["items"])

        for video in videos_found:
            video_id = video['id']
            channel_id = video['snippet']['channelId']
            upload_time = video['snippet']['publishedAt']
            video_title = video['snippet']['title']
            yield {'video_id': video_id, 'channel_id': channel_id, 'upload_time': upload_time,
                   'video_title': video_title}

    @staticmethod
    def _yt_to_channel_dict(response: Dict) -> Union[Dict, None]:
        """
        Transforms a YouTube API response into a channel Dict.

        Args:
            response:
        """

        for channel in response['items']:
            result = dict()
            result['channel_id'] = channel['id']
            result['username'] = channel['snippet']['title']
            result['added_on'] = datetime.utcnow().isoformat()
            result['last_commented'] = (datetime.utcnow() - timedelta(days=1)).isoformat()
            return result
        return None

    @staticmethod
    def split_list(input_list: List, chunk_size: int) -> List:
        """
        Split a list into `chunk_size` sub-lists.

        Args:
            input_list:
            chunk_size:
        """

        chunks = math.ceil(len(input_list) / chunk_size)
        if chunks == 1:
            output_list = [input_list]
        else:
            output_list = []
            end = 0
            for i in range(chunks - 1):
                start = i * chunk_size
                end = (i + 1) * chunk_size
                output_list.append(input_list[start:end])
            output_list.append(input_list[end:])

        return output_list

    def _get_uploads_playlist(self, api, ch_id: str, uploads_list_id: str,
                              max_posted_hours: int = 2) -> Dict:
        """ Retrieves uploads using the specified playlist ID which were had been added
        since the last check.

        Args:
            api:
            ch_id (str):
            uploads_list_id (str): The ID of the uploads playlist
            max_posted_hours:
        """

        # Construct the request
        playlist_items_request = api.playlistItems().list(
            playlistId=uploads_list_id,
            part="snippet",
            fields='items(id,snippet(title,publishedAt,resourceId(videoId)))',
            maxResults=1
        )

        try:
            playlist_items_response = playlist_items_request.execute()
            for playlist_item in playlist_items_response["items"]:
                published_at = dateutil.parser.parse(playlist_item['snippet']['publishedAt'])
                video = dict()
                # Return the video only if it was published in the last `last_n_hours` hours
                if published_at >= (datetime.utcnow() - timedelta(hours=max_posted_hours)).replace(
                        tzinfo=timezone.utc):
                    video['id'] = playlist_item["snippet"]["resourceId"]["videoId"]
                    video['published_at'] = playlist_item["snippet"]["publishedAt"]
                    video['title'] = playlist_item["snippet"]["title"]
                    yield video
                else:
                    yield None
        except Exception as e:
            try:
                logger.error(e)
                if ch_id in self.channel_playlists:
                    logger.warn(f"Skipping upload list {uploads_list_id} for channel {ch_id}..")
                    del self.channel_playlists[ch_id]
            except Exception as e:
                logger.error(e)

    def _comment_threads_insert(self, properties: Dict, **kwargs: Any) -> Dict:
        """ Comment using the YouTube API.
        Args:
            properties:
            **kwargs:
        """

        resource = self._build_resource(properties)
        kwargs = self._remove_empty_kwargs(**kwargs)
        response = self._apis[0].commentThreads().insert(body=resource, **kwargs).execute()
        return response

    @staticmethod
    def _build_resource(properties: Dict) -> Dict:
        """ Build a resource based on a list of properties given as key-value pairs.
            Leave properties with empty values out of the inserted resource. """

        resource = {}
        for p in properties:
            # Given a key like "snippet.title", split into "snippet" and "title", where
            # "snippet" will be an object and "title" will be a property in that object.
            prop_array = p.split('.')
            ref = resource
            for pa in range(0, len(prop_array)):
                is_array = False
                key = prop_array[pa]
                # For properties that have array values, convert a name like
                # "snippet.tags[]" to snippet.tags, and set a flag to handle
                # the value as an array.
                if key[-2:] == '[]':
                    key = key[0:len(key) - 2:]
                    is_array = True
                if pa == (len(prop_array) - 1):
                    # Leave properties without values out of inserted resource.
                    if properties[p]:
                        if is_array:
                            ref[key] = properties[p].split(',')
                        else:
                            ref[key] = properties[p]
                elif key not in ref:
                    # For example, the property is "snippet.title", but the resource does
                    # not yet have a "snippet" object. Create the snippet object here.
                    # Setting "ref = ref[key]" means that in the next time through the
                    # "for pa in range ..." loop, we will be setting a property in the
                    # resource's "snippet" object.
                    ref[key] = {}
                    ref = ref[key]
                else:
                    # For example, the property is "snippet.description", and the resource
                    # already has a "snippet" object.
                    ref = ref[key]
        return resource

    @staticmethod
    def _remove_empty_kwargs(**kwargs: Any) -> Dict:
        """ Remove keyword arguments that are not set. """
        good_kwargs = {}
        if kwargs is not None:
            for key, value in kwargs.items():
                if value:
                    good_kwargs[key] = value
        return good_kwargs


class ParallelUploads:
    def __init__(self):
        self.uploads = []
        self.done = 0

    def get(self, channels, api, max_posted_hours, _get_uploads):
        try:
            for upload in _get_uploads(api=api,
                                       channels=channels,
                                       max_posted_hours=max_posted_hours):
                self.uploads.append(upload)
        except Exception as e:
            logger.error(e)
            self.done += 1
        self.done += 1
