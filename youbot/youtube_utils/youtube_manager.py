from typing import List, Tuple, Dict
from abc import ABC, abstractmethod
import os
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow
from oauth2client.client import OAuth2WebServerFlow
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
        print(type(self._api))

    @staticmethod
    def _build_api(client_id: str, client_secret: str, api_version: str, read_only_scope: str,
                   tag: str):
        # Build a youtube api connection
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
