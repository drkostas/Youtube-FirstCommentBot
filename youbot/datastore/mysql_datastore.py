from typing import List, Tuple, Dict

from datetime import datetime
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

    def execute_query(self, query: str, commit: bool = False,
                      fetchall: bool = False, fetchone: bool = False) -> List[Tuple]:
        """
        Execute a query in the DB.
        Args:
            query:
            commit:
            fetchall:
            fetchone:
        """

        logger.debug("Executing: %s" % query)
        try:
            self._cursor.execute(query)
            if commit:
                self.commit()
            if fetchall:
                return self._cursor.fetchall()
            if fetchone:
                return self._cursor.fetchone()
        except mysql.connector.errors.ProgrammingError as e:
            logger.error(f'MySQL Error: {e}')
            logger.error(f'Full Query: {query}')

    def create_table(self, table: str, schema: str) -> None:
        """
        Creates a table using the specified schema

        :param self:
        :param table:
        :param schema:
        :return:
        """

        query = "CREATE TABLE IF NOT EXISTS {table} ({schema})".format(table=table, schema=schema)
        self.execute_query(query, commit=True)

    def drop_table(self, table: str) -> None:
        """
        Drops the specified table if it exists

        :param self:
        :param table:
        :return:
        """

        query = "DROP TABLE IF EXISTS {table}".format(table=table)
        self.execute_query(query, commit=True)

    def truncate_table(self, table: str) -> None:
        """
        Truncates the specified table

        :param self:
        :param table:
        :return:
        """

        query = "TRUNCATE TABLE {table}".format(table=table)
        self.execute_query(query, commit=True)

    def insert_into_table(self, table: str, data: dict) -> None:
        """
        Inserts into the specified table a row based on a column_name: value dictionary

        :param self:
        :param table:
        :param data:
        :return:
        """

        data_str = ", ".join(
            list(map(lambda key, val: "{key}='{val}'".format(key=str(key), val=str(val)), data.keys(),
                     data.values())))

        query = "INSERT INTO {table} SET {data}".format(table=table, data=data_str)
        self.execute_query(query, commit=True)

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
            list(map(lambda key, val: "{key}='{val}'".format(key=str(key), val=str(val)),
                     set_data.keys(),
                     set_data.values())))

        query = "UPDATE {table} SET {data} WHERE {where}".format(table=table, data=set_data_str,
                                                                 where=where)
        self.execute_query(query, commit=True)

    def select_from_table(self, table: str, columns: str = '*', where: str = 'TRUE',
                          order_by: str = 'NULL', asc_or_desc: str = 'ASC', limit: int = 1000,
                          group_by: str = '', having: str = '') -> List[Tuple]:
        """
        Selects from a specified table based on the given columns, where, ordering and limit

        Args:
            table:
            columns:
            where:
            order_by:
            asc_or_desc:
            limit:
            group_by:
            having:
        """

        # Construct Group By
        if group_by:
            if having:
                having = f'HAVING {having}'
            group_by = f'GROUP BY {group_by} {having} '

        # Build the Query
        query = f"SELECT {columns} " \
                f"FROM {table} " \
                f"WHERE {where} " \
                f"{group_by}" \
                f"ORDER BY {order_by} {asc_or_desc} " \
                f"LIMIT {limit}"

        results = self.execute_query(query, fetchall=True)

        return results

    def select_join(self, left_table: str, right_table: str,
                    join_key_left: str, join_key_right: str,
                    left_columns: str = '', right_columns: str = '', custom_columns: str = '',
                    join_type: str = 'INNER',
                    where: str = 'TRUE', order_by: str = 'NULL', asc_or_desc: str = 'ASC',
                    limit: int = 1000, group_by: str = '', having: str = '') -> List[Tuple]:
        """
        Join two tables and select.

        Args:
            left_table:
            right_table:
            left_columns:
            right_columns:
            custom_columns: Custom columns for which no `l.` or `r.` will be added automatically
            join_key_left: The column of join of the left table
            join_key_right: The column of join of the right table
            join_type: OneOf(INNER, LEFT, RIGHT)
            where: Add a `l.` or `.r` before the specified columns
            order_by: Add a `l.` or `.r` before the specified columns
            asc_or_desc:
            limit:
            group_by: Add a `l.` or `.r` before the specified columns
            having: Add a `l.` or `.r` before the specified columns
        """

        # Construct Group By
        if group_by:
            if having:
                having = f'HAVING {having}'
            group_by = f'GROUP BY {group_by} {having} '

        # Construct Columns
        if left_columns:
            left_columns = 'l.' + ', l.'.join(map(str.strip, left_columns.split(',')))
            if right_columns or custom_columns:
                left_columns += ', '
        if right_columns:
            right_columns = 'r.' + ', r.'.join(map(str.strip, right_columns.split(',')))
            if custom_columns:
                right_columns += ', '
        columns = f'{left_columns} {right_columns} {custom_columns}'

        # Build the Query
        query = f"SELECT {columns} " \
                f"FROM {left_table} l " \
                f"{join_type} JOIN {right_table} r " \
                f"ON l.{join_key_left}=r.{join_key_right} " \
                f"WHERE {where} " \
                f"{group_by}" \
                f"ORDER BY {order_by} {asc_or_desc} " \
                f"LIMIT {limit}"

        print(query)
        results = self.execute_query(query, fetchall=True)

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
        self.execute_query(query, commit=True)

    def show_tables(self) -> List:
        """
        Show a list of the tables present in the db
        :return:
        """

        query = 'SHOW TABLES'
        results = self.execute_query(query, fetchall=True)

        return [result[0] for result in results]

    def commit(self) -> None:
        self._connection.commit()

    def close_connection(self) -> None:
        """
        Flushes and closes the connection

        :return:
        """

        self.commit()
        self._cursor.close()

    __exit__ = close_connection


class YoutubeMySqlDatastore(MySqlDatastore):
    CHANNEL_TABLE = 'channels'
    COMMENTS_TABLE = 'comments'

    def __init__(self, config: Dict) -> None:
        """
        The basic constructor. Creates a new instance of Datastore using the specified credentials

        :param config:
        """

        super().__init__(config)
        self.create_tables_if_not_exist()

    def create_tables_if_not_exist(self):
        channels_schema = \
            """
            channel_id     varchar(100) default ''   not null,
            username       varchar(100)              not null,
            added_on       varchar(100)              not null,
            last_commented varchar(100)              not null,
            priority       int auto_increment,
            channel_photo  varchar(100) default '-1' null,
            constraint id_pk PRIMARY KEY (channel_id),
            constraint channel_id unique (channel_id),
            constraint priority unique (priority),
            constraint username unique (username)"""
        comments_schema = \
            """
            channel_id   varchar(100)              not null,
            video_link   varchar(100)              not null,
            comment      varchar(255)              not null,
            comment_time varchar(100)              not null,
            like_count   int          default -1   null,
            reply_count  int          default -1   null,
            comment_id   varchar(100) default '-1' null,
            video_id     varchar(100) default '-1' null,
            comment_link varchar(100) default '-1' null,
            constraint video_link_pk PRIMARY KEY (video_link),
            constraint video_link     unique (video_link),
            constraint channel_id foreign key (channel_id) references channels (channel_id) on update cascade on delete cascade"""

        self.create_table(table=self.CHANNEL_TABLE, schema=channels_schema)
        self.create_table(table=self.COMMENTS_TABLE, schema=comments_schema)

    def get_channels(self) -> List[Tuple]:
        """ Retrieve all channels from the database. """

        result = self.select_from_table(table=self.CHANNEL_TABLE)

        return result

    def add_channel(self, channel_data: Dict) -> None:
        """ Insert the provided channel into the database"""

        try:
            self.insert_into_table(table=self.CHANNEL_TABLE, data=channel_data)
        except mysql.connector.errors.IntegrityError as e:
            logger.error(f"MySQL error: {e}")

    def get_channel_by_id(self, ch_id: str) -> Tuple:
        """Retrieve a channel from the database by its ID

        Args:
            ch_id (str): The channel ID
        """

        where_statement = f"id='{ch_id}'"
        result = self.select_from_table(table=self.CHANNEL_TABLE, where=where_statement)
        if len(result) > 1:
            logger.warning("Duplicate channel retrieved from SELECT statement:{result}")
        elif len(result) == 0:
            result.append(())

        return result[0]

    def get_channel_by_username(self, ch_username: str) -> Tuple:
        """Retrieve a channel from the database by its Username

        Args:
            ch_username (str): The channel ID
        """

        where_statement = f"username='{ch_username}'"
        result = self.select_from_table(table=self.CHANNEL_TABLE, where=where_statement)
        if len(result) > 1:
            logger.warning("Duplicate channel retrieved from SELECT statement:{result}")
        elif len(result) == 0:
            result.append(())

        return result[0]

    def remove_channel_by_id(self, ch_id: str) -> None:
        """Retrieve a channel from the database by its ID

        Args:
            ch_id (str): The channel ID
        """

        where_statement = f"id='{ch_id}'"
        self.delete_from_table(table=self.CHANNEL_TABLE, where=where_statement)

    def remove_channel_by_username(self, ch_username: str) -> None:
        """Delete a channel from the database by its Username

        Args:
            ch_username (str): The channel ID
        """

        where_statement = f"username='{ch_username}'"
        self.delete_from_table(table=self.CHANNEL_TABLE, where=where_statement)

    def update_channel_photo(self, channel_id: str, photo_url: str) -> None:
        """
        Update the profile picture link of a channel.
        Args:
            channel_id:
            photo_url:
        """

        set_data = {'channel_photo': photo_url}
        self.update_table(table=self.CHANNEL_TABLE,
                          set_data=set_data,
                          where=f"channel_id='{channel_id}'")

    def add_comment(self, ch_id: str, video_link: str, comment_text: str) -> None:
        """ TODO: check the case where a comment contains single quotes
        Add comment data and update the `last_commented` channel column.

        Args:
            ch_id:
            video_link:
            comment_text:
        """

        datetime_now = datetime.utcnow().isoformat()
        comments_data = {'channel_id': ch_id,
                         'video_link': video_link,
                         'comment': comment_text,
                         'comment_time': datetime_now}
        update_data = {'last_commented': datetime_now}
        where_statement = f"channel_id='{ch_id}'"

        try:
            self.insert_into_table(self.COMMENTS_TABLE, data=comments_data)
            # Update Channel's last_commented timestamp
            self.update_table(table=self.CHANNEL_TABLE, set_data=update_data, where=where_statement)
        except mysql.connector.errors.IntegrityError as e:
            logger.error(f"MySQL Error: {e}")

    def get_comments(self, n_recent: int, min_likes: int = -1,
                     min_replies: int = -1) -> List[Tuple]:
        """
        Get the latest n_recent comments from the comments table.
        Args:
            n_recent:
            min_likes:
            min_replies:
        """

        comment_cols = 'video_link, comment, comment_time, like_count, reply_count, comment_link'
        channel_cols = 'username, channel_photo'
        where = f'l.like_count>={min_likes} AND l.reply_count>={min_replies} '
        for comment in self.select_join(left_table=self.COMMENTS_TABLE,
                                        right_table=self.CHANNEL_TABLE,
                                        left_columns=comment_cols,
                                        right_columns=channel_cols,
                                        custom_columns='COUNT(comment) as cnt',
                                        join_key_left='channel_id',
                                        join_key_right='channel_id',
                                        where=where,
                                        order_by='l.comment_time',
                                        asc_or_desc='desc',
                                        limit=n_recent):
            yield comment

    def update_comment(self, video_link: str, comment_id: str,
                       like_cnt: int, reply_cnt: int) -> None:
        """
        Populate a comment entry with additional information.
        Args:
            video_link:
            comment_id:
            like_cnt:
            reply_cnt:
        """

        # Get video id
        video_id = video_link.split('v=')[1].split('&')[0]
        # Create Comment Link
        comment_link = f'https://youtube.com/watch?v={video_id}&lc={comment_id}'
        # Construct the update key-values
        set_data = {'comment_link': comment_link,
                    'video_id': video_id,
                    'comment_id': comment_id,
                    'like_count': like_cnt,
                    'reply_count': reply_cnt}
        # Execute the update command
        self.update_table(table=self.COMMENTS_TABLE,
                          set_data=set_data,
                          where=f"video_link='{video_link}'")

