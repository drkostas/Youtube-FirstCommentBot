from typing import List, Tuple, Dict, Union
from abc import ABC, abstractmethod
import os
import math
from datetime import datetime, timedelta, timezone
import dateutil.parser
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow
from oauth2client.client import OAuth2WebServerFlow
import googleapiclient
from googleapiclient.discovery import build
import httplib2

from youbot import ColorizedLogger

logger = ColorizedLogger('YoutubeManager')


class AbstractYoutubeManager(ABC):
    __slots__ = ('channel_name', '_api', 'tag')

    @abstractmethod
    def __init__(self, config: Dict, channel_name: str, tag: str) -> None:
        """
        The basic constructor. Creates a new instance of YoutubeManager using the specified credentials

        :param config:
        """

        self.channel_name = channel_name
        self.tag = tag
        self._api = self._build_api(**config, tag=self.tag)

    @staticmethod
    @abstractmethod
    def _build_api(*args, **kwargs):
        pass


class YoutubeManagerV3(AbstractYoutubeManager):
    def __init__(self, config: Dict, channel_name: str, tag: str):
        super().__init__(config, channel_name, tag)

    @staticmethod
    def _build_api(client_id: str, client_secret: str, api_version: str, read_only_scope: str,
                   tag: str) -> googleapiclient.discovery.Resource:
        """
        Build a youtube api connection.

        Args:
            client_id:
            client_secret:
            api_version:
            read_only_scope:
            tag:
        """

        flow = OAuth2WebServerFlow(client_id=client_id,
                                   client_secret=client_secret,
                                   scope=read_only_scope)
        key_path = os.path.join('..', 'keys', f'{tag}.json')
        storage = Storage(key_path)
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            flags = argparser.parse_args(args=['--noauth_local_webserver'])
            credentials = run_flow(flow, storage, flags)

        api = build('youtube', api_version, http=credentials.authorize(httplib2.Http()))
        return api

    @staticmethod
    def _channel_from_response(response: Dict) -> Union[Dict, None]:
        """
        Transforms a YouTube API response into a channel Dict.

        Args:
            response:
        """

        for channel in response['items']:
            result = dict()
            result['id'] = channel['id']
            result['username'] = channel['snippet']['title']
            result['title'] = None
            result['added_on'] = datetime.utcnow().isoformat()
            result['last_commented'] = (datetime.utcnow() - timedelta(days=1)).isoformat()
            return result
        return None

    def get_channel_info_by_username(self, username: str) -> Union[Dict, None]:
        """Queries YouTube for a channel using the specified username

        Args:
            username (str): The username to search for
        """

        channels_response = self._api.channels().list(
            forUsername=username,
            part="snippet",
            fields='items(id,snippet(title))'
        ).execute()
        if channels_response:
            channel = self._channel_from_response(channels_response)
            if channel is not None:
                channel['username'] = username
        else:
            logger.warning(f"Got empty response for channel username: {username}")
            channel = {}
        return channel

    def get_channel_info_by_id(self, channel_id: str) -> Union[Dict, None]:
        """ Queries YouTube for a channel using the specified channel id.

        Args:
            channel_id (str): The channel ID to search for
        """

        channels_response = self._api.channels().list(
            id=channel_id,
            part="snippet",
            fields='items(id,snippet(title))'
        ).execute()

        return self._channel_from_response(channels_response)

    def get_uploads(self, channels: List, last_n_hours: int = 2) -> Dict:
        """ Retrieves new uploads for the specified channels.

        Args:
            channels(list): A list with channel IDs
            last_n_hours:
        """

        # Separate the channels list in 50-sized channel lists
        channels_lists = self.split_list(channels, 50)
        channels_to_check = []
        # Get the Playlist IDs of each channel
        for channels in channels_lists:
            channels_response = self._api.channels().list(
                id=",".join(channels),
                part="contentDetails,snippet",
                fields="items(id,contentDetails(relatedPlaylists(uploads)),snippet(title))"
            ).execute()
            channels_to_check.extend(channels_response["items"])
        # For each playlist ID, get 50 videos
        for channel in channels_to_check:
            uploads_list_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
            for upload in self._get_uploads_playlist(uploads_list_id, last_n_hours):
                upload['channel_title'] = channel['snippet']['title']
                upload['channel_id'] = channel['id']
                yield upload

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

    def _get_uploads_playlist(self, uploads_list_id: str, last_n_hours: int = 2) -> Dict:
        """ Retrieves uploads using the specified playlist ID which were have been added
        since the last check.

        Args:
            uploads_list_id (str): The ID of the uploads playlist
        """

        # Construct the request
        playlist_items_request = self._api.playlistItems().list(
            playlistId=uploads_list_id,
            part="snippet",
            fields='items(id,snippet(title,publishedAt,resourceId(videoId)))',
            maxResults=50
        )

        while playlist_items_request:
            playlist_items_response = playlist_items_request.execute()
            for playlist_item in playlist_items_response["items"]:
                published_at = dateutil.parser.parse(playlist_item['snippet']['publishedAt'])
                video = dict()
                # Return the video only if it was published in the last `last_n_hours` hours
                if published_at >= (datetime.utcnow() - timedelta(hours=last_n_hours)).replace(
                        tzinfo=timezone.utc):
                    video['id'] = playlist_item["snippet"]["resourceId"]["videoId"]
                    video['published_at'] = playlist_item["snippet"]["publishedAt"]
                    video['title'] = playlist_item["snippet"]["title"]
                    yield video
                # else:
                #     return

            playlist_items_request = self._api.playlistItems().list_next(
                playlist_items_request, playlist_items_response
            )
