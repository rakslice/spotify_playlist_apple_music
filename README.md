# spotify\_playlist\_apple\_music

A quick script to get public Spotify playlists into Apple Music by automating keyboard and mouse input to iTunes in Windows.

Yes this is a dirty kludge you shouldn't want, but I'm putting it up in case it will give a head start to someone who decides to go down the same road. 

# To install

 First you'll need [Python 2.7](https://www.python.org/downloads/). 
 
Then, to install the other required libraries, run

    >C:\Python27\pip install -r requirements.txt

on the included requirements.txt file.

# To use

1. If you have a playlist with more than the first page of tracks (100+ tracks), the script will need to do JSON requests to Spotify for more pages of playlist. There is no Spotify authentication built-in; you'll need to get a Spotify Authorization header ("Bearer ...") and put it in `spotify_authorization.txt`

2. Launch iTunes

3. You'll need to get iTunes in the correct starting state by searching for a track in the Apple Music search and adding it to your target playlist. You can remove it again right away; this is just to get the "Add to Last Playlist, ~" context menu item to appear and to get the search in Apple Music mode. 

4. Run it:

    >c:\Python27\python spotify_playlist_apple_music.py --playlist-name "<name of your itunes playlist>" <open.spotify.com playlist web page URL>

5. If you need to exit, turn on Scroll Lock and the script will stop before the next track.

# Notes

- You may need to tweak the track/artist name matching code to get it to work for the tracks in your playlist.
- `LEAVE_OUT_PHRASES` has text fragments to not include in the Apple Music search
- `WORD_REPLACEMENTS` has word re-mappings to use in the search
- `TEXT_REPLACEMENTS` maps characters of the search to [pywinauto keyboard codes](https://pywinauto.readthedocs.io/en/latest/code/pywinauto.keyboard.html) (these appear to be based on [Windows virtual-key codes](https://msdn.microsoft.com/en-us/library/windows/desktop/dd375731(v=vs.85).aspx)) - you may need to alter this if you use a non-US keyboard or need additional symbols for your searches 
- As with all GUI automation of this nature, you may find it unreliable and need to adjust the timing rubber bands to get it to work on your system.
