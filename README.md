# tidal-utils

Are you tired of content silently leaking out of your TIDAL Collection? Me too. Thankfully, you've come to the right place! You can back up your collection now with `backup.py` and then use `compare_backups.py` in the future to identify any tracks, albums, or playlist tracks that may have leaked out.

Also, if you've noticed you have tracks, albums, or playlists in your TIDAL Collection that are greyed out and no longer playable, `fix_unavailable.py` will identify them and optionally try to replace them.

WARNING: Use `fix_unavailable.py` at your own risk. While I have tested it on my own library without incident, using the `-r` flag will instruct it to add and remove tracks and albums from your TIDAL Collection. So, I highly recommend you save a backup of your Collection with `backup.py` before running `fix_unavailable.py` with the `-r` flag in case it doesn't behave as you would expect.

Prerequisites: 

This code relies on the tidalapi module. Installation instructions and other documentation can be found on its [GitHub page](https://github.com/tamland/python-tidal).

Usage example:

`python3 /path/to/backup.py`

`python3 /path/to/compare_backups.py /path/to/backup_old.pkl /path/to/backup_new.pkl`

`python3 /path/to/fix_unavailable.py -r -f`

For help and more details, run:

`python3 /path/to/compare_backups.py -h`

`python3 /path/to/fix_unavailable.py -h`

### FAQ

**I don't know how to run Python code. How do I even use this?**

The first three sections of this [guide](https://www.freecodecamp.org/news/the-python-guide-for-beginners/) will get you up and running! You will still need to install the tidalapi module as called out above, but that's all there is to it.

**Can you add X feature or make Y change?**

Maybe. Search for any enhancement requests that match yours on the Issues tab, and create a new issue if none do.

**This was working fine but now I'm getting a strange error. How do I fix it?**

There were probably some changes made to the track metadata in tidalapi. Pull the newest code from this repository using `git pull` and update tidalapi using `pip install tidalapi -U`. That will most likely solve your problem.

**Something is actually broken. Can you fix it?**

I'll do my best. Search for any open issues on the Issues tab that match yours, and create a new issue if none do. I'll take a look at it when I can.
