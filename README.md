# tidal-utils

Are you tired of having to manually maintain your TIDAL music library when tracks become unavailable? Me too. Thankfully, you've come to the right place.

`fix_unavailable.py` will identify, and optionally try to replace, unvailable albums and tracks in your TIDAL Collection.
It can also optionally replace unavailable songs in playlists you've created, but be warned that the replacement tracks will be added to the very end of the playlist (see FAQ).

WARNING: Use this program at your own risk. While I have tested this code on my own library without incident, using the `-r` flag will instruct the program to add and remove tracks and albums from your TIDAL library. So, I highly recommend saving a backup of your library before running with the `-r` flag in case it doesn't behave as you would expect.

Prerequisites: 

This code relies on the tidalapi module. Installation instructions and other documentation can be found on its [GitHub page](https://github.com/tamland/python-tidal).

Usage example:

`python3 /path/to/fix_unavailable.py -r -f -p`

For help, run: 

`python3 /path/to/fix_unavailable.py -h`

### FAQ

**I don't know how to run Python code. How do I even use this?**

The first three sections of this [guide](https://www.freecodecamp.org/news/the-python-guide-for-beginners/) will get you up and running! You will still need to install the tidalapi module as called out above, but that's all there is to it.

**You suggested backing up my library before I run this. How do I do that?**

You could use a tool like [TuneMyMusic](https://tidal.com/transfer-music), or for a quick and dirty solution you could use `backup.py`.

**Something is broken. Can you fix it?**

I'll do my best. Search for any open issues on the Issues tab that match yours, and create a new issue if none do. I'll take a look at it when I can.

**Can you add X feature or make Y change?**

Maybe. Search for any enhancement requests that match yours on the Issues tab, and create a new issue if none do.

**Why is the track order not preserved in playlists when I run with the -p flag? Why are the replacement tracks added to the end?**

This is due to API limitations. You get this behavior if you use the playlist.add() and playlist.remove_by_id() methods, and I don't know of a better way of accmplishing this. I also considered: 

* Creating a brand new playlist with all tracks in the correct order. However, others may have added your existing playlist to their Collection, so there is value in editing an existing playlist rather than making a new one.
* Deleting all songs and re-adding all songs in the correct order. This would destroy the "Date Added" metadata, and it would also cause bigger problems than the other options if the API started failing before the job was done.

If you're familiar with [tidalapi](https://github.com/tamland/python-tidal) and know of a better way to do this, make sure no one's already made that suggestion on the Issues tab, and then create a new issue to let me know.
