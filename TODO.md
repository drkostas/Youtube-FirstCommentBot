# TODO
See the [issues](https://github.com/drkostas/youbot/issues) too.
## Done
- [X] Load starter
- [X] Get channel name automatically
- [X] Build YouTube Manager class
- [X] Create child MySQL class
- [X] Integrate YoutubeMysql class into the YoutubeManager class
- [X] Use the pypi packages I have created instead of the local ones
- [X] Find a better way to change priorities (probably add a function to push everything)
- [X] Create the workflow for the commenter
- [X] Roll the comments for each channel - store comments in sql table?
- [X] Store comments in dropbox
- [X] \[Merged\] Regularly backup logs files from logs/ to dropbox (for when running on Heroku) + Store errors in sql or dropbox
- [X] Ensure code works without dropbox and emailer modules
- [X] Create the workflow for the accumulator
- [X] Load yt keys from Dropbox
- [X] Add SQL scripts for creating the tables needed (automatically checks and creates on init)
- [X] Different YT env vars for each yml
- [X] Option to set username manually
- [X] Test that everything works properly
- [X] Configure Procfile and circleci config
- [X] Update Readme
- [X] Increase check speed the minutes before o'clock
- [X] Optimize SQL queries
- [X] Load comments & only before the loop to make every loop faster
- [X] Add Video Title
- [X] Recreate the Livestreaming module (In different private repo, will merge them at some point)
- [X] Use multiple accounts (different api keys) to check for new comments
- [X] Instead of retrieving the playlist id everytime, load when we need it
- [X] Slow Mode: Reduce check time in specific times (eg midnight to 6am)
- [X] Add option for channel to only use channel comments (when available)
- [X] Mandatory timeout per channel
## Important Features
- [ ] Threading to get batches of new videos in parallel
- [ ] Send me email on fatal error (on later version)
- [ ] Email me if there are replies mentioning the word "bot"
## Secondary
- [ ] Add seconds late column and update with accumulator
- [ ] Make get_video_comments() more efficient by loading 50 comments at a time
- [ ] In add_comment() use foreign keys to update the channels table and save time
- [ ] Optimize get_next_template_comment()
- [ ] Add more tests
- [ ] For very fast lookups using Redis would be optimal but an overkill at this point
