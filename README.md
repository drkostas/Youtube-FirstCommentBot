# Youtube Comment Bot

[![CircleCI](https://circleci.com/gh/drkostas/Youtube-FirstCommentBot/tree/master.svg?style=svg)](https://circleci.com/gh/drkostas/Youtube-FirstCommentBot/tree/master)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/drkostas/Youtube-FirstCommentBot/master/LICENSE)
<a href="https://www.buymeacoffee.com/drkostas" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="25" ></a>

## Table of Contents

+ [About](#about)
+ [Getting Started](#getting_started)
    + [Prerequisites](#prerequisites)
+ [Build and prepare the project](#build_prepare)
    + [Install the requirements](#install)
    + [Create the config files](#configs)
    + [Specify the pool of comments](#comments_pool)
    + [Start following channels](#add_channels)
+ [Run the Bot](#commenter)
+ [Gathering statistics about the comments](#accumulator)
+ [Using Dropbox](#dropbox)
+ [Deployment on Heroku](#heroku)
+ [Continuous Ιntegration](#ci)
+ [Todo](#todo)
+ [Built With](#built_with)
+ [License](#license)
+ [Acknowledgments](#acknowledgments)

## About <a name = "about"></a>

A bot that leaves the first comment on every new video of specified channels.

<b><u>DISCLAIMER: This project is built for educational purposes. DO NOT use it to create spam-bots.</u><b>

Current modules:

- Commenter: Looks for new videos indefinitely and leaves a comment as soon as something is posted
- Accumulator: Goes through all the comments posted and populates the `comments` table in the DB with
  metadata such as the likes and replies count
- List Channels: It lists the Channels that are currently followed by the bot
- List Comments: It lists all the Comments posted by the bot
- Add Channel: It adds a new channel to the following list
- Set Priority: It set the comment priority of a specified channel
- Refresh Photo: It gathers and populates the `channels` table in the DB with URLs to the Channels'
  profile photos

## Getting Started <a name = "getting_started"></a>

These instructions will get you a copy of the project up and running on your local machine for
development and testing purposes. See deployment for notes on how to deploy the project on a live
system.

### Prerequisites <a name = "prerequisites"></a>

You need to have a machine with Python >= 3.8 and any Bash-like shell (e.g. zsh) installed.

```ShellSession

$ python3.8 -V
Python 3.8

$ echo $SHELL
/usr/bin/zsh

```

This project requires a MySQL database and a YouTube API key. Optionally, you can also set up a Dropbox
API key which is very useful when you use Heroku to deploy the bot.

References:

- YouTube: Use the Google API Console to create OAuth 2.0 credentials:
    + Visit the [developer console](https://console.cloud.google.com/apis/dashboard)
    + Create a new project
    + Open the [API Manager](https://console.developers.google.com/apis/)
      + Enable YouTube Data API v3
    + Go to [Consent](https://console.cloud.google.com/apis/credentials/consent)
      + Create a new OAuth client ID
      + Configure the OAuth consent screen
      + Use Type: External
      + Provide a client name (e.g. YoutubeBot)
      + Fill in the support email and developer contact information sections
      + Click Continue and add the youtube.force-ssl scope
      + Click Save and Continue again and go back to dashboard
      + Click Publish App in the consent section (testing only lasts for 10 days)
    + Go to [Credentials](https://console.cloud.google.com/apis/credentials)
      + Type: Web Application
      + Authorized Redirect URIs: http://localhost:8080/
      + Copy Client ID and secret to the respective vars in your config file
    + The first time you use the credentials the app will redirect you to a webpage
      + Login with the Google account you used
      + Click Advanced -> "Go to <name> (unsafe)"
      + Click Continue
    + Your Credentials are set up!
    + (*Warning*: The default quota limit per day is around 10,000 which is only enough for having 2 channels. You should request a quota increase if you want more.)
- MySQL: If you don't have DB already, you can create one for free with Amazon RDS:
  [Reference 1](https://aws.amazon.com/rds/free/),
  [Reference 2](https://bigdataenthusiast.wordpress.com/2016/03/05/aws-rds-instance-setup-oracle-db-on-cloud-free-tier/)
- Dropbox: How to set up an API key for your Dropbox account:
  [Reference 1](http://99rabbits.com/get-dropbox-access-token/),
  [Reference 2](https://dropbox.tech/developers/generate-an-access-token-for-your-own-account)

## Build and prepare the project <a name = "build_prepare"></a>

This section will go through the installation steps, setting up the configuration files and comments,
and preparing the DB tables.

### Install the requirements <a name = "install"></a>

All the installation steps are handled by the [Makefile](Makefile). By default, it uses `conda`
environments. If you want to use `virtualenv` instead, append to every `make` command the flag:
`env=venv`. If you want to modify the name of the environment or use another python version, modify the
first lines of the [Makefile](Makefile).

Deactivate and active Conda environment, install the requirements and load the newly created
environment:

```ShellSession
$ conda deactivate
$ make install
$ conda activate youbot
```

### Create the config files <a name = "configs"></a>

The project uses YML config files along with command-line arguments. There are three configs I am using:

- [generic.yml](confs/generic.yml): Used for running the following commands:
    - list_channels
    - list_comments
    - add_channel
    - remove_channel
    - refresh_photos
    - set_priority
- [commenter.yml](confs/commenter.yml): Used to run the `commenter` command
  - One thing to bear in mind here is that the bot checks and comments only on videos not commented 
  yet. So  the first time your run it you don't want to comment on every single video in the past few 
  days. So make sure you set the `max_posted_hours` option to 1 and increase it the next days 
  if you want.
- [accumulator.yml](confs/accumulator.yml): Used to run the `accumulator` command

I am not going to go into depth for each available setting because you can use the three YML files as
templates. The only thing that should be mentioned is that I am using environmental variables to set
most of the values. For example: `db_name: !ENV ${MYSQL_DB_NAME}`. You can replace
the `!ENV ${MYSQL_DB_NAME}`
part with the actual value, for example: `db_name: My_Database`. For more details on how to use env
variables check [these instructions](https://pypi.org/project/yaml-config-wrapper/).

### Specify the pool of comments <a name = "comments_pool"></a>

Now, you don't want the bot to post the same comment over and over again. For that reason, I am using a
pool of available comments, and the bot automatically picks one that hasn't been commented on to the
respective channel yet, otherwise, it picks the one that was posted the longest time ago. Just create
a `default.txt` file in a folder named `comments` and write one comment per line. If, for a specific
channel, you want to have additional comments, create another txt file named after the channel's id.
For example, you can create a `UC-ImLFXGIe2FC4Wo5hOodnw.txt` for the Veritasium YT channel that 
has that id.

### Start following channels <a name = "add_channels"></a>

We are now ready to add YT channels to our following list (stored in the DB). After ensuring you are in
the Conda environment, use the following command to add channels:

Using the channel ID

```ShellSession
$ python youbot/run.py -c confs/generic.yml -l logs/generic.log -m add_channel -i <channel id>
```

Using the channel username (Fails most of the time)

```ShellSession
$ python youbot/run.py -c confs/generic.yml -l logs/generic.log -m add_channel -u <channel username>
```

To view the followed channels run:

```ShellSession
$ python youbot/run.py -c confs/generic.yml -l logs/generic.log -m list_channels
```

Similarly, to remove a channel run:
```ShellSession
$ python youbot/run.py -c confs/generic.yml -l logs/generic.log -m remove_channel -i <channel id>
```

There is also the option to set the priorities of each channel. If 2 or more channels post videos at
the same time, the bot will leave comments first to the ones with the highest priority value. To do so
run the following:

```ShellSession
$ python youbot/run.py -c confs/generic.yml -l logs/generic.log -m set_priority --priority <priority num> -i <channel id>
```

After you're done, you can optionally populate the table with each channel's profile picture:

```ShellSession
$ python youbot/run.py -c confs/generic.yml -l logs/generic.log -m refresh_photos
```

## Run the Bot <a name = "commenter"></a>

Now we are ready to run the commenter module of the bot. Assuming you set up the channels, created the
configuration, and you have the comments ready, run the following command:

```ShellSession
python youbot/run.py -c confs/commenter.yml -l logs/commenter.log -m commenter
```

The bot will then run indefinitely until you stop it.

You can view all the comments posted at any point with the following command:

```ShellSession
python youbot/run.py -c confs/generic.yml -l logs/generic.log -m list_comments --n-recent 10
```

## Gathering statistics about the comments <a name = "accumulator"></a>

Now that the bot is running, you probably want to gather statistics about the comments such as the
number of likes and replies. There is another bot for that job, that also runs indefinitely and
constantly updates the data in the `comments` table. To start it run the following command:

```ShellSession
python youbot/run.py -c confs/accumulator.yml -l logs/accumulator.log -m accumulator
```

## Using Dropbox <a name = "dropbox"></a>

There is the option to also incorporate dropbox in the whole pipeline. Assuming you already created an
API key and added a cloudstore section in the config, you can use the following options:

- `load_keys_from_cloud: true` (under youtube config): If set to true, the bot will automatically copy
  the JSON keys from the defined `keys_folder_path` setting (in cloudstore config) to the defined
  `keys` setting (in youtube config). This is very useful if you deploy the bot to Heroku which is
  stateless and any newly created file can be deleted anytime. So you may have to manually recreate the
  keys.
- `upload_logs_every: 15` (under cloudstore config): If you configured the cloudstore config for the
  commenter, then the bot will automatically copy the log file to the cloudstore `logs_folder_path`
  every 15 `While: True` loops in the commenter function. Again, very useful for keeping the logs while
  running on Heroku.
- `comments: type: dropbox`: If you set the type of the `comments` setting as `dropbox` then the
  commenter will download the comment txt files from `dropbox_folder_name` into `local_folder_name`
  before every `While: True` loop in the commenter. Useful for modifying the comments when running on
  Heroku.

## Deployment on Heroku <a name = "heroku"></a>

The deployment is being done to <b>Heroku</b>. For more information, you can check
the [setup guide](https://devcenter.heroku.com/articles/getting-started-with-python).

Make sure you check the defined [Procfile](Procfile)
([reference](https://devcenter.heroku.com/articles/getting-started-with-python#define-a-procfile))
and that you set the appropriate environmental variables
([reference](https://devcenter.heroku.com/articles/config-vars)).

## Continuous Integration <a name = "ci"></a>

For the continuous integration, the <b>CircleCI</b> service is being used. For more information, you can
check the [setup guide](https://circleci.com/docs/2.0/language-python/).

Again, you should set the appropriate environmental variables 
([reference](https://circleci.com/docs/2.0/env-vars/#setting-an-environment-variable-in-a-context))
and for any modifications, edit the [circleci config](/.circleci/config.yml).

## TODO <a name = "todo"></a>

Read the [TODO](TODO.md) to see the current task list.

## License <a name = "license"></a>

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

