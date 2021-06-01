from typing import List, Tuple, Dict

from mysql import connector as mysql_connector
import mysql.connector.cursor

from .abstract_datastore import AbstractDatastore
from youbot import ColorizedLogger

logger = ColorizedLogger('MySqlDataStore')


class MySqlDatastore(AbstractDatastore):
    __slots__ = ('_connection', '_cursor')

    _connection: mysql_connector.MySQLConnection
    _cursor: mysql_connector.cursor.MySQLCursor

    def __init__(self, config: Dict) -> None:
        """
        The basic constructor. Creates a new instance of Datastore using the specified credentials

        :param config:
        """

        super().__init__(config)

    @staticmethod
    def get_connection(username: str, password: str, hostname: str, db_name: str, port: int = 3306) \
            -> Tuple[mysql_connector.MySQLConnection, mysql_connector.cursor.MySQLCursor]:
        """
        Creates and returns a connection and a cursor/session to the MySQL DB

        :param username:
        :param password:
        :param hostname:
        :param db_name:
        :param port:
        :return:
        """

        connection = mysql_connector.connect(
            host=hostname,
            user=username,
            passwd=password,
            database=db_name,
            use_pure=True
        )

        cursor = connection.cursor()
        return connection, cursor

    def create_table(self, table: str, schema: str) -> None:
        """
        Creates a table using the specified schema

        :param self:
        :param table:
        :param schema:
        :return:
        """

        query = "CREATE TABLE IF NOT EXISTS {table} ({schema})".format(table=table, schema=schema)
        logger.debug("Executing: %s" % query)
        self._cursor.execute(query)
        self._connection.commit()

    def drop_table(self, table: str) -> None:
        """
        Drops the specified table if it exists

        :param self:
        :param table:
        :return:
        """

        query = "DROP TABLE IF EXISTS {table}".format(table=table)
        logger.debug("Executing: %s" % query)
        self._cursor.execute(query)
        self._connection.commit()

    def truncate_table(self, table: str) -> None:
        """
        Truncates the specified table

        :param self:
        :param table:
        :return:
        """

        query = "TRUNCATE TABLE {table}".format(table=table)
        logger.debug("Executing: %s" % query)
        self._cursor.execute(query)
        self._connection.commit()

    def insert_into_table(self, table: str, data: dict) -> None:
        """
        Inserts into the specified table a row based on a column_name: value dictionary

        :param self:
        :param table:
        :param data:
        :return:
        """

        data_str = ", ".join(
            list(map(lambda key, val: "{key}='{val}'".format(key=str(key), val=str(val)), data.keys(), data.values())))

        query = "INSERT INTO {table} SET {data}".format(table=table, data=data_str)
        logger.debug("Executing: %s" % query)
        self._cursor.execute(query)
        self._connection.commit()

    def update_table(self, table: str, set_data: dict, where: str) -> None:
        """
        Updates the specified table using a column_name: value dictionary and a where statement

        :param self:
        :param table:
        :param set_data:
        :param where:
        :return:
        """

        set_data_str = ", ".join(
            list(map(lambda key, val: "{key}='{val}'".format(key=str(key), val=str(val)), set_data.keys(),
                     set_data.values())))

        query = "UPDATE {table} SET {data} WHERE {where}".format(table=table, data=set_data_str, where=where)
        logger.debug("Executing: %s" % query)
        self._cursor.execute(query)
        self._connection.commit()

    def select_from_table(self, table: str, columns: str = '*', where: str = 'TRUE', order_by: str = 'NULL',
                          asc_or_desc: str = 'ASC', limit: int = 1000) -> List:
        """
        Selects from a specified table based on the given columns, where, ordering and limit

        :param self:
        :param table:
        :param columns:
        :param where:
        :param order_by:
        :param asc_or_desc:
        :param limit:
        :return results:
        """

        query = "SELECT {columns} FROM  {table} WHERE {where} ORDER BY {order_by} {asc_or_desc} LIMIT {limit}".format(
            columns=columns, table=table, where=where, order_by=order_by, asc_or_desc=asc_or_desc, limit=limit)
        logger.debug("Executing: %s" % query)
        self._cursor.execute(query)
        results = self._cursor.fetchall()

        return results

    def delete_from_table(self, table: str, where: str) -> None:
        """
        Deletes data from the specified table based on a where statement

        :param self:
        :param table:
        :param where:
        :return:
        """

        query = "DELETE FROM {table} WHERE {where}".format(table=table, where=where)
        logger.debug("Executing: %s" % query)
        self._cursor.execute(query)
        self._connection.commit()

    def show_tables(self) -> List:
        """
        Show a list of the tables present in the db
        :return:
        """

        query = 'SHOW TABLES'
        logger.debug("Executing: %s" % query)
        self._cursor.execute(query)
        results = self._cursor.fetchall()

        return [result[0] for result in results]

    def __exit__(self) -> None:
        """
        Flushes and closes the connection

        :return:
        """

        self._connection.commit()
        self._cursor.close()
