from youbot import ColorLogger, HighMySQL
from typing import *
from datetime import datetime

logger = ColorLogger(logger_name="YoutubeMySqlDatastore", color="red")


class YoutubeMySqlDatastore(HighMySQL):
    CHANNEL_TABLE = "channels"
    COMMENTS_TABLE = "comments"

    def __init__(self, config: Dict, tag: str) -> None:
        """
        The basic constructor. Creates a new instance of Datastore using the specified credentials
        :param config:
        :param tag:
        """
        global logger
        logger = ColorLogger(logger_name=f"[{tag}] YoutubeMySqlDatastore", color="red")
        super().__init__(config)
        self.create_tables_if_not_exist()

    def create_tables_if_not_exist(self):
        channels_schema = """
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
        comments_schema = """
            channel_id   varchar(100)              not null,
            video_link   varchar(100)              not null,
            comment      varchar(255)              not null,
            comment_time varchar(100)              not null,
            upload_time varchar(100)              not null,
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
        """Retrieve all channels from the database."""
        if comment_cols is not None:
            result = self.select_join(
                left_table=self.CHANNEL_TABLE,
                right_table=self.COMMENTS_TABLE,
                left_columns=",".join(channel_cols),
                right_columns=",".join(comment_cols),
                join_key_left="channel_id",
                join_key_right="channel_id",
                order_by="l.delay_comment, l.priority",
                asc_or_desc="asc",
                join_type=join_type,
                where=where,
            )
            col_names = channel_cols + comment_cols
        elif complex_sort_key is None:
            result = self.select_from_table(
                table=self.CHANNEL_TABLE,
                columns=",".join(channel_cols),
                order_by="delay_comment, priority",
                asc_or_desc="asc",
                where=where,
            )
            col_names = channel_cols
            for row in result:
                yield self._row_to_dict(row, col_names)
        else:
            max_key = -1
            while True:
                table = (
                    "(SELECT * "
                    f"FROM {self.CHANNEL_TABLE} "
                    f"WHERE priority>{max_key} "
                    "ORDER BY priority "
                    "LIMIT 50) a"
                )
                result = list(
                    self.select_from_table(
                        table=table,
                        columns=",".join(channel_cols),
                        order_by="delay_comment, priority",
                        asc_or_desc="asc",
                        where=where,
                    )
                )
                if len(result) == 0:
                    break
                max_key = sorted(result, key=lambda x: x[complex_sort_key])[-1][
                    complex_sort_key
                ]
                col_names = channel_cols
                for row in result:
                    yield self._row_to_dict(row, col_names)

    def add_channel(self, channel_data: Dict) -> None:
        """Insert the provided channel into the database"""

        try:
            # TODO: Implement if_not_exists=True in HighMySQL
            self.insert_into_table(table=self.CHANNEL_TABLE, data=channel_data)
        except Exception as e:
            # TODO: except HighMySQL.mysql.connector.errors.IntegrityError as e:
            # Expose mysql in HighMySQL
            logger.error(f"MySQL error: {e}")

    def set_priority(self, channel_data: Dict, priority: str) -> None:
        """Insert the provided channel into the database"""
        priority = int(priority)
        req_priority = priority
        req_channel_id = channel_data["channel_id"]
        channels = list(
            self.get_channels(channel_cols=["channel_id", "priority"], where="TRUE")
        )
        try:
            # Give all channels a temp priority
            for channel in channels:
                channel_id = channel["channel_id"]
                # Execute the update command
                self.update_table(
                    table=self.CHANNEL_TABLE,
                    set_data={"priority": -int(channel["priority"])},
                    where=f"channel_id='{channel_id}'",
                )
            # Update the other channels
            ch_cnt = 1
            for channel in channels:
                channel_id = channel["channel_id"]
                if channel_id == req_channel_id:
                    continue
                if channel["priority"] < req_priority:
                    set_data = {"priority": ch_cnt}
                    ch_cnt += 1
                else:
                    set_data = {"priority": priority + 1}
                    priority += 1
                # Execute the update command
                self.update_table(
                    table=self.CHANNEL_TABLE,
                    set_data=set_data,
                    where=f"channel_id='{channel_id}'",
                )
            # Update the requested channel
            self.update_table(
                table=self.CHANNEL_TABLE,
                set_data={"priority": req_priority},
                where=f"channel_id='{req_channel_id}'",
            )
        except Exception as e:
            # TODO: except HighMySQL.mysql.connector.errors.IntegrityError as e:
            # Expose mysql in HighMySQL
            logger.error(f"MySQL error: {e}")

    def set_likes(self, channel_id: Dict, likes: Union[str, int]) -> None:
        """Insert the provided channel into the database"""
        likes = int(likes)

        # Execute the update command
        self.update_table(
            table=self.CHANNEL_TABLE,
            set_data={"target_likes": likes},
            where=f"channel_id='{channel_id}'",
        )

    def get_channel_by_id(self, ch_id: str) -> Tuple:
        """Retrieve a channel from the database by its ID
        Args:
            ch_id (str): The channel ID
        """

        where_statement = f"channel_id='{ch_id}'"
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

    def get_non_ordered_comments(self, max_minutes: int):
        """Retrieve all comments that are not ordered"""
        comment_cols = ["comment_id", "video_link"]
        channel_cols = ["target_likes"]
        where_statement = "ordered is FALSE AND "
        where_statement += "l.comment_id != '-1' AND "
        where_statement += "l.comment != '-1'AND "
        where_statement += (
            f"l.comment_time > DATE_SUB(NOW(), INTERVAL {max_minutes} MINUTE) "
        )
        result = self.select_join(
            left_table=self.COMMENTS_TABLE,
            right_table=self.CHANNEL_TABLE,
            left_columns=",".join(comment_cols),
            right_columns=",".join(channel_cols),
            join_key_left="channel_id",
            join_key_right="channel_id",
            where=where_statement,
            order_by="comment_time",
            asc_or_desc="desc",
            limit=9999,
            join_type="INNER",
        )
        return result

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

        set_data = {"channel_photo": photo_url}
        self.update_table(
            table=self.CHANNEL_TABLE,
            set_data=set_data,
            where=f"channel_id='{channel_id}'",
        )

    def add_comment(
        self,
        ch_id: str,
        video_link: str,
        comment_text: str,
        upload_time: str,
        video_title: str,
        comment_id: str,
    ) -> None:
        """TODO: check the case where a comment contains single quotes
        Add comment data and update the `last_commented` channel column.
        Args:
            ch_id:
            video_link:
            comment_text:
            upload_time:
        """

        datetime_now = datetime.utcnow().isoformat()
        comments_data = {
            "channel_id": ch_id,
            "video_link": video_link,
            "comment": comment_text.replace("'", "''"),
            "comment_id": comment_id,
            "comment_time": datetime_now,
            "upload_time": upload_time,
        }
        update_data = {"last_commented": datetime_now}
        where_statement = f"channel_id='{ch_id}'"

        try:
            self.insert_into_table(self.COMMENTS_TABLE, data=comments_data)
            # Update Channel's last_commented timestamp
            # TODO: Do that with foreign keys
            self.update_table(
                table=self.CHANNEL_TABLE, set_data=update_data, where=where_statement
            )
        except Exception as e:
            # TODO: except HighMySQL.mysql.connector.errors.IntegrityError as e:
            # Expose mysql in HighMySQL
            logger.error(f"MySQL Error: {e}")

    def get_comments(
        self,
        comment_cols: List[str],
        channel_cols: List[str] = None,
        n_recent: int = 50,
        min_likes: int = -1,
        max_likes: int = 999999,
        min_replies: int = -1,
        max_replies: int = 999999,
        channel_id: str = None,
        only_valid_comment_texts: bool = False,
        only_valid_comment_ids: bool = False,
        only_null_upload: bool = False,
        only_null_comment_id: bool = False,
        only_null_video_title: bool = False,
        order_by: str = "comment_time",
        join_type: str = "INNER",
    ) -> List[Dict]:
        """
        Get the latest n_recent comments from the comments table.
        Args:
            n_recent:
            min_likes:
            min_replies:
            max_replies:
            channel_id:
            only_null_upload:
            only_null_comment_id:
            only_null_video_title:
            order_by:
            join_type:
        """

        where = (
            f"like_count>={min_likes} AND reply_count>={min_replies} AND "
            f"like_count<={max_likes} AND reply_count<={max_replies} "
        )
        if channel_id is not None:
            where += f"AND channel_id='{channel_id}' "
        if only_null_upload is True:
            where += "AND (upload_time='None' OR upload_time='-1') "
        if only_null_comment_id is True:
            where += "AND (comment_id='None' OR comment_id='-1') "
        if only_null_video_title is True:
            where += "AND (video_title='None' OR video_title='-1') "
        if only_valid_comment_texts is True:
            where += "AND (comment!='-1') "
        if only_valid_comment_ids is True:
            where += "AND (comment_id!='-1') "

        if channel_cols is not None:
            result = self.select_join(
                left_table=self.COMMENTS_TABLE,
                right_table=self.CHANNEL_TABLE,
                left_columns=",".join(comment_cols),
                right_columns=",".join(channel_cols),
                join_key_left="channel_id",
                join_key_right="channel_id",
                where=where,
                order_by=order_by,
                asc_or_desc="desc",
                limit=n_recent,
                join_type=join_type,
            )
            col_names = comment_cols + channel_cols
        else:
            result = self.select_from_table(
                table=self.COMMENTS_TABLE,
                columns=",".join(comment_cols),
                where=where,
                order_by=order_by,
                asc_or_desc="desc",
                limit=n_recent,
            )
            col_names = comment_cols
        for row in result:
            yield self._row_to_dict(row, col_names)

    def update_comment(
        self,
        video_link: str,
        comment_id: str = None,
        like_cnt: int = None,
        reply_cnt: int = None,
        upload_time: str = None,
        video_title: str = None,
        comment_time: str = None,
        ordered: str = None,
    ) -> None:
        """
        Populate a comment entry with additional information.
        Args:
            video_link:
            comment_id:
            like_cnt:
            reply_cnt:
        """

        # Get video id
        video_id = video_link.split("v=")[1].split("&")[0]
        # Create Comment Link
        comment_link = f"https://youtube.com/watch?v={video_id}&lc={comment_id}"
        # Construct the update key-values
        set_data = {}
        if video_id is not None:
            set_data["video_id"] = video_id
        if comment_id is not None:
            set_data["comment_id"] = comment_id
            # Create Comment Link
            comment_link = f"https://youtube.com/watch?v={video_id}&lc={comment_id}"
            set_data["comment_link"] = comment_link
        if like_cnt is not None:
            set_data["like_count"] = like_cnt
        if reply_cnt is not None:
            set_data["reply_count"] = reply_cnt
        if comment_time is not None:
            set_data["comment_time"] = comment_time
        if upload_time is not None:
            set_data["upload_time"] = upload_time
        if video_title is not None:
            set_data["video_title"] = video_title.replace("'", "''")
        if ordered is not None:
            set_data["ordered"] = ordered

        # Execute the update command
        self.update_table(
            table=self.COMMENTS_TABLE,
            set_data=set_data,
            where=f"video_link='{video_link}'",
        )

    # TODO: Add this to HighMySQL
    def select_join(
        self,
        left_table: str,
        right_table: str,
        join_key_left: str,
        join_key_right: str,
        left_columns: str = "",
        right_columns: str = "",
        custom_columns: str = "",
        join_type: str = "INNER",
        where: str = "TRUE",
        order_by: str = "NULL",
        asc_or_desc: str = "ASC",
        limit: int = 1000,
        group_by: str = "",
        having: str = "",
    ) -> List[Tuple]:
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
                having = f"HAVING {having}"
            group_by = f"GROUP BY {group_by} {having} "

        # Construct Columns
        if left_columns:
            left_columns = "l." + ", l.".join(map(str.strip, left_columns.split(",")))
            if right_columns or custom_columns:
                left_columns += ", "
        if right_columns:
            right_columns = "r." + ", r.".join(map(str.strip, right_columns.split(",")))
            if custom_columns:
                right_columns += ", "
        columns = f"{left_columns} {right_columns} {custom_columns}"

        # Build the Query
        query = (
            f"SELECT {columns} "
            f"FROM {left_table} l "
            f"{join_type} JOIN {right_table} r "
            f"ON l.{join_key_left}=r.{join_key_right} "
            f"WHERE {where} "
            f"{group_by}"
            f"ORDER BY {order_by} {asc_or_desc} "
            f"LIMIT {limit}"
        )

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
        channel["channel_id"] = row[0]
        channel["username"] = row[1]
        channel["added_on"] = row[2]
        channel["last_commented"] = row[3]
        channel["priority"] = row[4]
        channel["channel_photo"] = row[5]
        return channel

    @staticmethod
    def _table_row_to_comment_dict(row: Tuple) -> Dict:
        """Transform a table row into a channel representation
        Args:
            row (list): The database row
        """

        channel = dict()
        channel["video_link"] = row[0]
        channel["comment"] = row[1]
        channel["comment_time"] = row[2]
        channel["like_count"] = row[3]
        channel["reply_count"] = row[4]
        channel["comment_link"] = row[5]
        channel["username"] = row[6]
        channel["channel_photo"] = row[7]
        return channel
