# tidal-utils

Are you tired of having to manually maintain your TIDAL music library when tracks become unavailable? Me too. Thankfully, you've come to the right place.

`fix_unavailable.py` will identify, and optionally try to replace, unvailable albums and tracks in your TIDAL Collection.

WARNING: Use this program at your own risk. While I have tested this code on my own library without incident, using the `-r` flag will instruct the program to add and remove tracks and albums from your TIDAL library. So, I highly recommend saving a backup of your library before running with the `-r` flag in case it doesn't behave as you would expect.

Prerequisites: 

This code relies on the tidalapi module. Installation instructions and other documentation can be found on its [GitHub page](https://github.com/tamland/python-tidal).

Usage example:

`python3 /path/to/fix_unavailable.py -r -f`

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
