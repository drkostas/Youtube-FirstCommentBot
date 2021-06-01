from typing import List, Dict
import logging
from gmail import GMail, Message

from .abstract_emailer import AbstractEmailer
from youbot import ColorizedLogger

logger = ColorizedLogger('GmailEmailer')


class GmailEmailer(AbstractEmailer):
    __slots__ = ('_handler', 'email_address', 'test_mode')

    _handler: GMail
    test_mode: bool

    def __init__(self, config: Dict, test_mode: bool = False) -> None:
        """
        The basic constructor. Creates a new instance of EmailApp using the specified credentials

        :param config:
        :param test_mode:
        """

        self.email_address = config['email_address']
        self._handler = self.get_handler(email_address=self.email_address,
                                         api_key=config['api_key'])
        self.test_mode = test_mode
        super().__init__()

    @staticmethod
    def get_handler(email_address: str, api_key: str) -> GMail:
        """
        Returns an EmailApp handler.

        :param email_address:
        :param api_key:
        :return:
        """

        gmail_handler = GMail(username=email_address, password=api_key)
        gmail_handler.connect()
        return gmail_handler

    def is_connected(self) -> bool:
        return self._handler.is_connected()

    def get_self_email(self):
        return self.email_address

    def send_email(self, subject: str, to: List, cc: List = None, bcc: List = None, text: str = None,
                   html: str = None,
                   attachments: List = None, sender: str = None, reply_to: str = None) -> None:
        """
        Sends an email with the specified arguments.

        :param subject:
        :param to:
        :param cc:
        :param bcc:
        :param text:
        :param html:
        :param attachments:
        :param sender:
        :param reply_to:
        :return:
        """

        if self.test_mode:
            to = self.email_address
            cc = self.email_address if cc is not None else None
            bcc = self.email_address if bcc is not None else None

        msg = Message(subject=subject,
                      to=",".join(to),
                      cc=",".join(cc) if cc is not None else None,
                      bcc=",".join(bcc) if cc is not None else None,
                      text=text,
                      html=html,
                      attachments=attachments,
                      sender=sender,
                      reply_to=reply_to)
        logger.debug("Sending email with Message: %s" % msg)
        self._handler.send(msg)

    def __exit__(self):
        self._handler.close()
