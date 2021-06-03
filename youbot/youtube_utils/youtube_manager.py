from typing import List, Tuple, Dict
from abc import ABC, abstractmethod

from youbot import ColorizedLogger

logger = ColorizedLogger('YoutubeManager')


class AbstractYoutubeManager(ABC):
    __slots__ = ('channel_name', '_api')

    @abstractmethod
    def __init__(self, config: Dict, channel_name: str) -> None:
        """
        The basic constructor. Creates a new instance of YoutubeManager using the specified credentials

        :param config:
        """

        self.channel_name = channel_name
        self._api = self._build_api(**config)

    @staticmethod
    @abstractmethod
    def _build_api(*args, **kwargs):
        pass


class YoutubeManagerV3(AbstractYoutubeManager):
    def __init__(self, config: Dict, channel_name: str):
        super().__init__(config, channel_name)

    @staticmethod
    def _build_api(client_id: str, client_secret: str, api_version: str, read_only_scope: str):
        # Build a youtube api connection
        return 'test'
