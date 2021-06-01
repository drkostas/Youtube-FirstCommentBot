from abc import ABC, abstractmethod


class AbstractFancyLogger(ABC):
    """Abstract class of the FancyLog package"""

    @abstractmethod
    def __init__(self, *args, **kwargs) -> None:
        """The basic constructor. Creates a new instance of FancyLog using the
        specified arguments

        Args:
            *args:
            **kwargs:
        """

    @abstractmethod
    def create_logger(self, *args, **kwargs):
        pass
