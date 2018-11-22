# -*- coding: utf-8 -*-

import os
import google.oauth2.credentials
import requests
from bs4 import BeautifulSoup
import random
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
import webbrowser
from oauth2client.client import OAuth2WebServerFlow
from oauth2client import tools
from oauth2client.file import Storage


# Build a resource based on a list of properties given as key-value pairs.
# Leave properties with empty values out of the inserted resource.
def build_resource(properties):
	resource = {}
	for p in properties:
		# Given a key like "snippet.title", split into "snippet" and "title", where
		# "snippet" will be an object and "title" will be a property in that object.
		prop_array = p.split('.')
		ref = resource
		for pa in range(0, len(prop_array)):
			is_array = False
			key = prop_array[pa]
			# For properties that have array values, convert a name like
			# "snippet.tags[]" to snippet.tags, and set a flag to handle
			# the value as an array.
			if key[-2:] == '[]':
				key = key[0:len(key)-2:]
				is_array = True
			if pa == (len(prop_array) - 1):
				# Leave properties without values out of inserted resource.
				if properties[p]:
					if is_array:
						ref[key] = properties[p].split(',')
					else:
						ref[key] = properties[p]
			elif key not in ref:
				# For example, the property is "snippet.title", but the resource does
				# not yet have a "snippet" object. Create the snippet object here.
				# Setting "ref = ref[key]" means that in the next time through the
				# "for pa in range ..." loop, we will be setting a property in the
				# resource's "snippet" object.
				ref[key] = {}
				ref = ref[key]
			else:
				# For example, the property is "snippet.description", and the resource
				# already has a "snippet" object.
				ref = ref[key]
	return resource

# Remove keyword arguments that are not set
def remove_empty_kwargs(**kwargs):
	good_kwargs = {}
	if kwargs is not None:
		for key, value in kwargs.items():
			if value:
				good_kwargs[key] = value
	return good_kwargs


def comment_threads_insert(client, properties, **kwargs):
	# Add the comment
	resource = build_resource(properties)
	kwargs = remove_empty_kwargs(**kwargs)
	response = client.commentThreads().insert(body=resource,**kwargs).execute()
	return True


def Comment(api, video_id, channel_title):
	file_path = 'comments/{}_comments.txt'.format(channel_title)
	# If comments file for this channel doesn't exist, create it and add default comment.
	if not os.path.exists(file_path):
		f = open(file_path, 'w', encoding="ISO-8859-1")
		f.write("First Comment!") # Default Comment to add when no comments file exists for this channel
		f.close()

	# Take a comment at random and post it!
	with open(file_path, 'r', encoding="ISO-8859-1") as f:
		comments_list = [line.strip() for line in f]
	try:
		comment_text = random.choice(comments_list)
		print("\n\nNew Video!")
		print("Comment to add: ", comment_text)
		comment_threads_insert(api,
		{'snippet.channelId': 'UC7HIr-gmYyPJvGjKO0A6t5w',
		 'snippet.videoId': video_id,
		 'snippet.topLevelComment.snippet.textOriginal': comment_text},
		part='snippet')
		print("Comment added.")
	except BaseException as bs:
		print("An error occured:")
		print(bs)
	print("Video Details: ")

