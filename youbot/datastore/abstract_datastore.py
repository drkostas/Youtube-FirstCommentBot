from abc import ABC, abstractmethod
from typing import List, Dict


class AbstractDatastore(ABC):
    __slots__ = ('_connection', '_cursor')

    @abstractmethod
    def __init__(self, config: Dict) -> None:
        """
        Tha basic constructor. Creates a new instance of Datastore using the specified credentials

        :param config:
        """

        self._connection, self._cursor = self.get_connection(username=config['username'],
                                                             password=config['password'],
                                                             hostname=config['hostname'],
                                                             db_name=config['db_name'],
                                                             port=config['port'])

    @staticmethod
    @abstractmethod
    def get_connection(username: str, password: str, hostname: str, db_name: str, port: int):
        pass

    @abstractmethod
    def create_table(self, table: str, schema: str):
        pass

    @abstractmethod
    def drop_table(self, table: str) -> None:
        pass

    @abstractmethod
    def truncate_table(self, table: str) -> None:
        pass

    @abstractmethod
    def insert_into_table(self, table: str, data: dict) -> None:
        pass

    @abstractmethod
    def update_table(self, table: str, set_data: dict, where: str) -> None:
        pass

    @abstractmethod
    def select_from_table(self, table: str, columns: str = '*', where: str = 'TRUE',
                          order_by: str = 'NULL',
                          asc_or_desc: str = 'ASC', limit: int = 1000) -> List:
        pass

    @abstractmethod
    def delete_from_table(self, table: str, where: str) -> None:
        pass

    @abstractmethod
    def show_tables(self, *args, **kwargs) -> List:
        pass
