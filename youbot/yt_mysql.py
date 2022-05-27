from youbot import ColorLogger, HighMySQL
from typing import *
from datetime import datetime

logger = ColorLogger('YoutubeMySqlDatastore')


class YoutubeMySqlDatastore(HighMySQL):
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

    def get_channels(self) -> List[Dict]:
        """ Retrieve all channels from the database. """

        result = self.select_from_table(table=self.CHANNEL_TABLE, order_by='priority')
        for row in result:
            yield self._table_row_to_channel_dict(row, )

    def add_channel(self, channel_data: Dict) -> None:
        """ Insert the provided channel into the database"""

        try:
            self.insert_into_table(table=self.CHANNEL_TABLE, data=channel_data, if_not_exists=True)
        except HighMySQL.mysql.connector.errors.IntegrityError as e:
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
        except HighMySQL.mysql.connector.errors.IntegrityError as e:
            logger.error(f"MySQL Error: {e}")

    def get_comments(self, n_recent: int = 50, min_likes: int = -1,
                     min_replies: int = -1) -> List[Dict]:
        """
        Get the latest n_recent comments from the comments table.
        Args:
            n_recent:
            min_likes:
            min_replies:
        """
        self.select_from_table(self.COMMENTS_TABLE)

        comment_cols = 'video_link, comment, comment_time, like_count, reply_count, comment_link'
        channel_cols = 'username, channel_photo'
        where = f'l.like_count>={min_likes} AND l.reply_count>={min_replies} '
        for comment in self.select_join(left_table=self.COMMENTS_TABLE,
                                        right_table=self.CHANNEL_TABLE,
                                        left_columns=comment_cols,
                                        right_columns=channel_cols,
                                        join_key_left='channel_id',
                                        join_key_right='channel_id',
                                        where=where,
                                        order_by='l.comment_time',
                                        asc_or_desc='desc',
                                        limit=n_recent):
            yield self._table_row_to_comment_dict(comment)

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

        logger.debug("Executing: %s" % query)
        self._cursor.execute(query)
        results = self._cursor.fetchall()

        return results

    @staticmethod
    def _table_row_to_channel_dict(row: Tuple) -> Dict:
        """Transform a table row into a channel representation
        Args:
            row (list): The database row
        """

        channel = dict()
        channel['channel_id'] = row[0]
        channel['username'] = row[1]
        channel['added_on'] = row[2]
        channel['last_commented'] = row[3]
        channel['priority'] = row[4]
        channel['channel_photo'] = row[5]
        return channel

    @staticmethod
    def _table_row_to_comment_dict(row: Tuple) -> Dict:
        """Transform a table row into a channel representation
        Args:
            row (list): The database row
        """

        channel = dict()
        channel['video_link'] = row[0]
        channel['comment'] = row[1]
        channel['comment_time'] = row[2]
        channel['like_count'] = row[3]
        channel['reply_count'] = row[4]
        channel['comment_link'] = row[5]
        channel['username'] = row[6]
        channel['channel_photo'] = row[7]
        return channel
