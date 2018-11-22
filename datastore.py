from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from datetime import datetime

class DataStore():
	def __init__(self, user, password, hostname, dbname):
		"""Creates a new instance of the data store using the specified schema

		Args:
			db_path (str): The path where the database should be stored
			schema_path (str): The path to the SQL schema of the database
		"""

		self.engine = create_engine("mysql://{}:{}@{}/{}".format(user, password, hostname, dbname))
		self.session_obj = sessionmaker(bind=self.engine)
		self.session = scoped_session(self.session_obj)


	def __exit__(self):
		self.session.flush()
		self.session.commit()


	def channel_from_row(self, row):
		"""Transform a database row into a channel representation

		Args:
			row (list): The database row
		"""
		channel = dict()
		channel['id'] = row[0]
		channel['username'] = row[1]
		channel['title'] = row[2]
		channel['added_on'] = row[3]
		channel['last_checked'] = row[4]
		return channel


	def row_from_channel(self, channel):
		"""Transform a channel object into a database row

		Args:
			channel (dict): The channel object
		"""
		return (channel['id'], channel['username'], channel['title'], channel['added_on'], channel['last_checked'])


	def store_channel(self, channel):
		"""Insert the provided channel object into the database"""
		session = self.session
		session.execute('INSERT INTO channel VALUES ( "{}", "{}", "{}", "{}", "{}")'.format(*self.row_from_channel(channel)))
		session.commit()


	def get_channel_by_id(self, id):
		"""Retrieve a channel from the database by its ID

		Args:
			id (str): The channel ID
		"""
		session = self.session
		result = session.execute('SELECT * FROM channel WHERE id = {}'.format(id)).fetchone()
		if result is not None:
			return self.channel_from_row(result)
		return None


	def get_channel_by_username(self, username):
		"""Retrieve a channel from the database by its username

		Args:
			id (str): The username of the channel owner
		"""
		session = self.session
		result = session.execute('SELECT * FROM channel WHERE username = {}'.format(username)).fetchone()
		if result is not None:
			return self.channel_from_row(result)
		return None


	def get_channels(self):
		"""Retrieve all channels from the database"""
		session = self.session
		for row in session.execute('SELECT * FROM channel'):
			yield self.channel_from_row(row)
		return None


	def remove_channel(self, channel):
		"""Remove a channel from the database

		Args:
			channel (dict): The channel to be removed (by key 'id')
		"""
		session = self.session
		session.execute('DELETE FROM channel WHERE id = "{}"'.format(channel['id']))
		session.commit()


	def update_last_checked(self, channel_id):
		"""Update the last_checked value of a specific channel

		Args:
			channel_id (str): The channel to be updated
		"""
		session = self.session
		session.execute('UPDATE channel SET last_checked = "{}" WHERE id = "{}"'.format(datetime.utcnow().isoformat(), channel_id))
		session.commit()
