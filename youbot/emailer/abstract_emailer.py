from abc import ABC, abstractmethod


class AbstractEmailer(ABC):
    __slots__ = ('_handler',)

    @abstractmethod
    def __init__(self, *args, **kwargs) -> None:
        """
        Tha basic constructor. Creates a new instance of EmailApp using the specified credentials

        """

        pass

    @staticmethod
    @abstractmethod
    def get_handler(*args, **kwargs):
        """
        Returns an EmailApp handler.

        :param args:
        :param kwargs:
        :return:
        """

        pass

    @abstractmethod
    def send_email(self, *args, **kwargs):
        """
        Sends an email with the specified arguments.

        :param args:
        :param kwargs:
        :return:
        """

        pass
