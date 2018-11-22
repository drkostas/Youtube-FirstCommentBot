#!/bin/env python3
import sys
import argparse
import arrow
import time
from youtubeapi import YouTube
from datastore import DataStore
from commenter import Comment

def print_from_youtube(headers, data):
    """Print the provided header and data in a visually pleasing manner

    Args:
        headers (list of str): The headers to print
        data (list of list of str): The data rows
    """

    if (len(data) == 0):
        return
    separators = []
    for word in headers:
        separators.append('-' * len(word))
    output = [headers, separators] + data
    col_widths = [0] * len(headers)
    for row in output:
        for idx, column in enumerate(row):
            if len(column) > col_widths[idx]:
                col_widths[idx] = len(column)
    for row in output:
        for idx, column in enumerate(row):
            print("".join(column.ljust(col_widths[idx])), end = ' ' * 2)
        print()

def print_from_database(store):
    print("{}".format("_"*186))
    print("|{:-^30}|{:-^30}|{:-^60}|{:-^30}|{:-^30}|".format('ID', 'Username', 'Title', 'Added On', 'Last Checked'))
    for item in store.get_channels():
        print("|{:^30}|{:^30}|{:^60}|{:^30}|{:^30}|".format(item['id'], item['username'], str(item['title']), arrow.get(item['added_on']).humanize(), arrow.get(item['last_checked']).humanize()))
    print("|{}|".format("_"*184))

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--id', help = 'Channel ID', default = None)
    parser.add_argument('-u', '--username', help = 'Username', default = None)
    parser.add_argument('action', help = 'Perform the specified action', default = 'check',
        nargs = '?', choices = ['add', 'check', 'list', 'remove'])
    return parser

def main():
    """Parse the command line arguments, expecting one of the following formats:
        -) (-i ChannelID | -u Username) (add | check | remove)
        -) check | list
    and perform the appropriate action
    """
    print("Starting..")
    parser = get_parser()
    args = parser.parse_args()

    youtube = YouTube()
    store = DataStore('username', 'passw', 'host', 'dbname') # Your db credentials

    channel = None
    if args.username is not None:
        channel = youtube.get_channel_by_username(args.username)
    elif args.id is not None:
        channel = youtube.get_channel_by_id(args.id)

    if args.action == 'add':
        store.store_channel(channel)
    elif args.action == 'remove':
        store.remove_channel(channel)
    elif args.action == 'list':
        print_from_database(store)
    elif args.action == 'check':
        print("Done! Waiting for new videos to be uploaded..")
        while True:
            # If the user passed a specific channel, check for new uploads
            # otherwhise check for uploads from every previously added channel
            channels = []
            if channel is not None:
                channels.append(store.get_channel_by_id(channel['id']))
            else:
                channels = store.get_channels()

            data = []
            to_check = dict()
            for channel_item in channels:
                to_check[channel_item['id']] = channel_item['last_checked']

            uploads = youtube.get_uploads(to_check)
            try:
                for upload in uploads:
                    current_link = 'https://youtube.com/watch?v=%s' % (upload['id'], )
                    data.append([
                        upload['channel_title'],
                        upload['title'],
                        arrow.get(upload['published_at']).humanize(),
                        current_link
                    ])
                    Comment(youtube.api, upload['id'], upload['channel_title'])

                print_from_youtube(['Channel', 'Title', 'Published', 'Link'], data)

                for channel_id in to_check.keys():
                    store.update_last_checked(channel_id)

                # Look for new videos every 15 seconds
                time.sleep(15)
            except BaseException as be:
                # If it reaches the 100 seconds api threshold, wait for 100 seconds
                print("Error: Too many requests:\n{}".format(be))
                print("Waiting 100 seconds..")
                time.sleep(100)
                print("Waiting for new videos to be uploaded..")

if __name__ == '__main__':
    main()
