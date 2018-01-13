""" This is a little GUI to launch the playlist importer.
It launches the import script in a command prompt window.
"""

import os
import urllib2

import subprocess

import sys

# This requires wxPython 3.0.2.0.
# For compatibility with virtualenv you can use the wheels from
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#wxpython
# (Download the "win32" or "amd64" wheel to match your python version, as well as the "common" wheel;
# pip install the common wheel first and then the architecture-specific one)

# noinspection PyUnresolvedReferences,PyPackageRequirements
import wx

import spotify_playlist_apple_music
from gui_autogen import MyFrame
from win_util import get_short_path_name


def set_enabled(obj, value):
    if value:
        obj.Enable()
    else:
        obj.Disable()


class MyFrameImpl(MyFrame):
    def __init__(self, *args, **kwargs):
        super(MyFrameImpl, self).__init__(*args, **kwargs)
        self.radio_btn_prefix.SetValue(True)
        self.have_loaded_playlist_ok = False
        self.loaded_playlist_name = None
        self.update_state()

    def update_state(self):
        prefix_mode = self.radio_btn_prefix.GetValue()
        set_enabled(self.text_playlist_name, not prefix_mode)
        set_enabled(self.text_prefix, prefix_mode)

        url_ready = self.text_url.GetValue() != ""
        set_enabled(self.button_load, url_ready)

        set_enabled(self.button_import, self.have_loaded_playlist_ok)

    def load_reset(self):
        self.have_loaded_playlist_ok = False
        self.loaded_playlist_name = None

    def radio_btn_change(self, event):
        self.load_reset()
        self.update_state()

    def text_url_change(self, event):
        self.load_reset()
        self.update_state()

    def text_prefix_change(self, event):
        self.load_reset()
        self.update_state()

    def text_playlist_name_change(self, event):
        self.load_reset()
        self.update_state()

    def button_load_click(self, event):
        self.have_loaded_playlist_ok = False
        self.update_state()
        url = self.text_url.GetValue()
        result = False
        try:
            it = spotify_playlist_apple_music.get_track_iterator_for_url(url)
            it.next()
        except KeyError:
            message = "Don't know how to load a playlist for this site. Double-check the URL."
        except urllib2.HTTPError:
            message = "Can't load the playlist at that address. Double-check the URL."
        else:
            prefix_mode = self.radio_btn_prefix.GetValue()
            imported_playlist_name = spotify_playlist_apple_music.loaded_playlist_name
            if prefix_mode:
                prefix = self.text_prefix.GetValue()
                if prefix is None:
                    prefix = ""
                playlist_name = prefix + imported_playlist_name
            else:
                playlist_name = self.text_playlist_name.GetValue()
            message = u"Loaded playlist. Click Import to create '%s'" % playlist_name
            result = True
        self.label_load_result.SetLabel(message)
        self.have_loaded_playlist_ok = result
        self.update_state()

    def button_import_click(self, event):
        params = []

        prefix_mode = self.radio_btn_prefix.GetValue()
        if prefix_mode:
            prefix_text = self.text_prefix.GetValue()
            if prefix_text != "":
                params += ["--playlist-prefix", '"%s"' % prefix_text]
        else:
            playlist_name_text = self.text_playlist_name.GetValue()
            params += ["--playlist-name", '"%s"' % playlist_name_text]

        url = self.text_url.GetValue()
        params.append(url)

        script_path = os.path.dirname(os.path.abspath(__file__))
        python_app = os.path.join(script_path, "spotify_playlist_apple_music.py")

        # I'm just using this short path name business because I can't find any quoting to convince
        # cmd /k to accept the
        python_exe = os.path.join(os.path.dirname(sys.executable), "python.exe")
        python_cmd = [get_short_path_name(python_exe), "-u", get_short_path_name(python_app)] + params

        command = "cmd /C start %s" % " ".join(python_cmd)
        print command
        subprocess.Popen(command, universal_newlines=True)


def main():
    app = wx.App()
    frame = MyFrameImpl(None)
    frame .Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
