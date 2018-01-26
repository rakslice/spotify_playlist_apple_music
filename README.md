# spotify\_playlist\_apple\_music

A quick script to get public Spotify playlists into Apple Music by automating keyboard and mouse input to iTunes in Windows.

Yes this is a dirty kludge you shouldn't want, but I'm putting it up in case it will give a head start to someone who decides to go down the same road. 

# To install

 First you'll need [Python 2.7](https://www.python.org/downloads/). 
 
Then, to install the other required libraries, run

    >C:\Python27\pip install -r requirements.txt

on the included requirements.txt file.

I've found that `win32api` installed this way fails to load unless you copy the `*.dll` files that it puts in `Lib/site-packages/pywin32_system32` in your python install or virtualenv to your `Lib/site-packages/win32` directory.

There is a GUI wrapper included (`gui.py`); you'll need to install wxPython 3.0 for Python 2.7 to use it.  For a wxPython build that's easy to use with `pip` and `virtualenv`, use [the unofficial Windows wheel builds from UCI](https://www.lfd.uci.edu/~gohlke/pythonlibs/#wxpython). You'll need to install both the common one

    pip install wxPython_common‑3.0.2.0‑py2‑none‑any.whl

and the `win32` or `win_amd64` one depending on whether your Windows version is 32-bit or 64-bit, respectively:

    pip install wxPython‑3.0.2.0‑cp27‑none‑*.whl

If you're okay with just running `spotify_playlist_apple_music.py` on the command line without using the GUI, you don't need to install wxPython.

# Command-line options

	usage: spotify_playlist_apple_music.py [-h] [--playlist-name PLAYLIST_NAME]
	                                       [--exists]
	                                       url
	
	positional arguments:
	  url                   An open.spotify.com URL for the public playlist to
	                        import
	
	optional arguments:
	  -h, --help            show this help message and exit
	  --playlist-name PLAYLIST_NAME
	                        The name of the iTunes playlist to create or add to.
	                        (default: use the name from the spotify playlist)
	  --exists              Expect an existing last playlist instead of creating a
	                        playlist at the start

# To use

1. If you have a playlist with more than the first page of tracks (100+ tracks), the script will need to do JSON requests to Spotify for more pages of playlist. There is no Spotify authentication built-in; you'll need to get a Spotify Authorization header ("`Bearer `...") and put it in `spotify_authorization.txt`

2. Launch iTunes

3. Run it:
    
    	>c:\Python27\python spotify_playlist_apple_music.py <open.spotify.com playlist web page URL>

4. If you need to exit, turn on Scroll Lock and the script will stop before the next track.

# Notes

- iTunes' search box needs to be in Apple Music mode. If you run into problems just type something into the search box and click the "All Apple Music" button on the right side of the pop-up (if you don't see it, make sure iTunes is logged in to your Apple account with an active Apple Music subscription).
- By default, the Spotify playlist name will be used as the iTunes playlist name; pass `--playlist-name <something else>` to use something else as the playlist name 
- If you want to add to an existing playlist (`--exists`), you'll need to get iTunes in the correct starting state by searching for a track in the Apple Music search and adding it to your target playlist. You can remove it again right away; this is just to get the *"Add to Last Playlist, {your playlist name}"* context menu choice to appear.
- You may need to tweak the track/artist name matching code to get it to work for the tracks in your playlist.
- `LEAVE_OUT_PHRASES` has text fragments to not include in the Apple Music search
- `WORD_REPLACEMENTS` has word re-mappings to use in the search
- `CHARACTER_CODES` maps characters of the search to [pywinauto keyboard codes](https://pywinauto.readthedocs.io/en/latest/code/pywinauto.keyboard.html) (these appear to be based on [Windows virtual-key codes](https://msdn.microsoft.com/en-us/library/windows/desktop/dd375731(v=vs.85).aspx)) - you may need to alter this if you use a non-US keyboard or need additional symbols for your searches 
- As with all GUI automation of this nature, you may find it unreliable and need to adjust the timing rubber bands to get it to work on your system.
