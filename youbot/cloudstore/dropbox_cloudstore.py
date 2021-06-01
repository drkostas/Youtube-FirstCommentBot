from typing import Dict, Union
from dropbox import Dropbox, files, exceptions

from .abstract_cloudstore import AbstractCloudstore
from youbot import ColorizedLogger

logger = ColorizedLogger('DropboxCloudstore')


class DropboxCloudstore(AbstractCloudstore):
    __slots__ = '_handler'

    _handler: Dropbox

    def __init__(self, config: Dict) -> None:
        """
        The basic constructor. Creates a new instance of Cloudstore using the specified credentials

        :param config:
        """

        self._handler = self.get_handler(api_key=config['api_key'])
        super().__init__()

    @staticmethod
    def get_handler(api_key: str) -> Dropbox:
        """
        Returns a Cloudstore handler.

        :param api_key:
        :return:
        """

        dbx = Dropbox(api_key)
        return dbx

    def upload_file(self, file_bytes: bytes, upload_path: str, write_mode: str = 'overwrite') -> None:
        """
        Uploads a file to the Cloudstore

        :param file_bytes:
        :param upload_path:
        :param write_mode:
        :return:
        """

        # TODO: Add option to support FileStream, StringIO and FilePath
        try:
            logger.debug("Uploading file to path: %s" % upload_path)
            self._handler.files_upload(f=file_bytes, path=upload_path,
                                       mode=files.WriteMode(write_mode))
        except exceptions.ApiError as err:
            logger.error('API error: %s' % err)

    def download_file(self, frompath: str, tofile: str = None) -> Union[bytes, None]:
        """
        Downloads a file from the Cloudstore

        :param frompath:
        :param tofile:
        :return:
        """

        try:
            if tofile is not None:
                logger.debug("Downloading file from path: %s to path %s" % (frompath, tofile))
                self._handler.files_download_to_file(download_path=tofile, path=frompath)
            else:
                logger.debug("Downloading file from path: %s to variable" % frompath)
                md, res = self._handler.files_download(path=frompath)
                data = res.content  # The bytes of the file
                return data
        except exceptions.HttpError as err:
            logger.error('HTTP error %s' % err)
            return None

    def delete_file(self, file_path: str) -> None:
        """
        Deletes a file from the Cloudstore

        :param file_path:
        :return:
        """

        try:
            logger.debug("Deleting file from path: %s" % file_path)
            self._handler.files_delete_v2(path=file_path)
        except exceptions.ApiError as err:
            logger.error('API error %s' % err)

    def ls(self, path: str = '') -> Dict:
        """
        List the files and folders in the Cloudstore

        :param path:
        :return:
        """
        try:
            files_list = self._handler.files_list_folder(path=path)
            files_dict = {}
            for entry in files_list.entries:
                files_dict[entry.name] = entry
            return files_dict
        except exceptions.ApiError as err:
            logger.error('Folder listing failed for %s -- assumed empty: %s' % (path, err))
            return {}
