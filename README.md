# tidal-utils

Are you tired of having to manually maintain your TIDAL Collection when tracks become unavailable? Me too. Thankfully, you've come to the right place! `fix_unavailable.py` will identify, and optionally try to replace, unavailable albums and tracks in your TIDAL Collection.

If you've noticed that songs are falling out of your TIDAL Collection entirely, you can back up your collection now with `backup.py` and then use `compare_backups.py` in the future to identify any tracks or albums that leaked out. This behavior started for tracks and albums in Summer 2025. Tracks in playlists that drop off TIDAL still become unavailable as before, though, and can be cleaned up with `fix_unavailable.py`.

WARNING: Use this program at your own risk. While I have tested this code on my own library without incident, using `fix_unavailable.py` with the `-r` flag will instruct the program to add and remove tracks and albums from your TIDAL Collection. So, I highly recommend you save a backup of your Collection before running `fix_unavailable.py` with the `-r` flag in case it doesn't behave as you would expect.

Prerequisites: 

This code relies on the tidalapi module. Installation instructions and other documentation can be found on its [GitHub page](https://github.com/tamland/python-tidal).

Usage example:

`python3 /path/to/fix_unavailable.py -r -f`

`python3 /path/to/compare_backups.py /path/to/backup_old.pkl /path/to/backup_new.pkl`

`python3 /path/to/backup.py`

For help, run: 

`python3 /path/to/fix_unavailable.py -h`

`python3 /path/to/compare_backups.py -h`

### FAQ

**I don't know how to run Python code. How do I even use this?**

The first three sections of this [guide](https://www.freecodecamp.org/news/the-python-guide-for-beginners/) will get you up and running! You will still need to install the tidalapi module as called out above, but that's all there is to it.

**You suggested backing up my library before I run this. How do I do that?**

You could use a tool like [TuneMyMusic](https://tidal.com/transfer-music), or for a quick and dirty solution you could use `backup.py`.

**Something is broken. Can you fix it?**

I'll do my best. Search for any open issues on the Issues tab that match yours, and create a new issue if none do. I'll take a look at it when I can.

**Can you add X feature or make Y change?**

Maybe. Search for any enhancement requests that match yours on the Issues tab, and create a new issue if none do.

**This was working fine but now I'm getting an error about is_DolbyAtmos. How do I fix it?**

There were some changes to the track metadata in tidalapi. Pull the newest code from this repository using `git pull` and update tidalapi using `pip install tidalapi -U`. That should solve your problem. 
