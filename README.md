# Youtube FIrst Commenter Bot

A bot that takes a list of youtube channels and posts the first comment in every new video.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

1. Use Google API Console to create OAuth 2.0 credentials:
   1. Visit the [developer console](https://console.developers.google.com)
   1. Create a new project
   1. Open the [API Manager](https://console.developers.google.com/apis/)
   1. Enable *YouTube Data API v3*
   1. Go to [Credentials](https://console.developers.google.com/apis/credentials)
   1. Configure the OAuth consent screen and create *OAuth client ID* credentials 
   1. Use Application Type *Other* and provide a client name (e.g. *Python*)
   1. Confirm and download the generated credentials as JSON file
1. Store the file in the application folder as *keys/client_secrets.json*


### Installing

Installing the requirements

```
pip install -r requirements.txt
```

Create a database named email with the following structure (I suggest using the free-tier Amazon RDS):

	+--------------+--------------+------+-----+
	| Field        | Type         | Null | Key |
	+--------------+--------------+------+-----+
	| id           | varchar(100) | NO   | PRI |
	| username     | varchar(100) | NO   | UNI |
	| title        | varchar(100) | YES  |     |
	| added_on     | varchar(100) | NO   |     |
	| last_checked | varchar(100) | NO   |     |
	+--------------+--------------+------+-----+

You will also need to add your information as follows:

checker.py

	store = DataStore('username', 'passw', 'host', 'dbname') # Your db credentials - line 60

youtubeapi.py

	CLIENT_SECRETS_FILE = "keys/client_secrets.json" # The location of the secrets file - line 19
	CLIENT_ID = "Your Client Id" # line 20
	CLIENT_SECRET = "Your Client Secret" # line 21

commenter.py

	f.write("First Comment!") # Default Comment to add when no comments file exists for this channel - line 80

Lastly, run `python3 checker.py -i CHANNEL_ID add` or `python3 checker.py -u CHANNEL_NAME add` to add the Youtube Channels you want 
and go to */comments* and create a *CHANNEL_NAME_comments.txt* for each channel containing a comment in each row.
You can also let the script create the comments files with the default comment you specified and modify them later.

And your are good to go!

Run `python3 checker.py list` to see the Youtube Channels list, , 
`python3 checker.py -i CHANNEL_ID remove` or `python3 checker.py -u CHANNEL_NAME remove` to remove a Youtube Channel and 
`python3 checker.py` to run continuesly the script.

### Note: The first time a browser window should open asking for confirmation. The next times, it will connect automatically.

## Deployment

You can easily deploy it on heroku.com (Procfile will automatically run the script). 

## License

This project is licensed under the GNU General Public License v3.0 License
