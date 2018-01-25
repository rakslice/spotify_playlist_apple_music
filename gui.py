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
    """ Helper to enable/disable GUI control """
    if value:
        obj.Enable()
    else:
        obj.Disable()


class MyFrameImpl(MyFrame):
    """ Attach code to the MyFrame GUI skeleton from the wxGlade code generator """
    def __init__(self, *args, **kwargs):
        super(MyFrameImpl, self).__init__(*args, **kwargs)
        self.radio_btn_prefix.SetValue(True)
        self.have_loaded_playlist_ok = False
        self.loaded_playlist_name = None
        self.update_state()
        self.current_process = None

    def update_state(self):
        """ Update the state of controls based on other controls' entered values and
        whether a playlist is already loaded """
        prefix_mode = self.radio_btn_prefix.GetValue()
        set_enabled(self.text_playlist_name, not prefix_mode)
        set_enabled(self.text_prefix, prefix_mode)

        url_ready = self.text_url.GetValue() != ""
        set_enabled(self.button_load, url_ready)

        set_enabled(self.button_import, self.have_loaded_playlist_ok)

        if self.have_loaded_playlist_ok:
            self.button_import.SetDefault()
        else:
            self.button_load.SetDefault()

    def load_reset(self):
        """ Something has been changed that invalidates the previously loaded playlist """
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
        self.load_reset()
        self.update_state()
        url = self.text_url.GetValue()

        # Try to load the playlist, and show a message about the result.

        result = False
        try:
            it = spotify_playlist_apple_music.get_track_iterator_for_url(url)
            it.next()
        except KeyError:
            message = "Don't know how to load a playlist for this site. Double-check the URL."
        except urllib2.HTTPError:
            message = "Can't load the playlist at that address. Double-check the URL."
        else:
            playlist_name = self.get_playlist_name()
            message = u"Loaded playlist. Click Import to create '%s'" % playlist_name
            result = True
        self.show_message(message)
        self.have_loaded_playlist_ok = result
        # If the load was successful, this will enable the Import button.
        self.update_state()

    def get_playlist_name(self):
        imported_playlist_name = spotify_playlist_apple_music.loaded_playlist_name
        prefix_mode = self.radio_btn_prefix.GetValue()
        if prefix_mode:
            prefix = self.text_prefix.GetValue()
            if prefix is None:
                prefix = ""
            playlist_name = prefix + imported_playlist_name
        else:
            playlist_name = self.text_playlist_name.GetValue()
        return playlist_name

    def show_message(self, message):
        self.label_load_result.SetLabel(message)

    def button_import_click(self, event):
        if self.checkbox_separate_window.GetValue():
            params = ["--pause"]
            command_form = "cmd /C start %s"
        else:
            params = []
            command_form = "cmd /C %s"

        prefix_mode = self.radio_btn_prefix.GetValue()
        if prefix_mode:
            prefix_text = self.text_prefix.GetValue()
            if prefix_text != "":
                params += ["--playlist-prefix", '"%s"' % prefix_text]
        else:
            playlist_name_text = self.text_playlist_name.GetValue()
            params += ["--playlist-name", '"%s"' % playlist_name_text]

        url = self.text_url.GetValue()

        self.show_message("Importing '%s' to '%s'" % (url, self.get_playlist_name()))

        params.append(url)

        script_path = os.path.dirname(os.path.abspath(__file__))
        python_app = os.path.join(script_path, "spotify_playlist_apple_music.py")

        # I'm just using this short path name business because I can't find any quoting to convince
        # cmd /C to accept the full path
        python_exe = os.path.join(os.path.dirname(sys.executable), "python.exe")
        python_cmd = [get_short_path_name(python_exe), "-u", get_short_path_name(python_app)] + params

        command = command_form % " ".join(python_cmd)
        print command
        self.current_process = subprocess.Popen(command, universal_newlines=True)
        self.button_import.Disable()
        self.monitor()

    def monitor(self):
        return_code = self.current_process.poll()
        if return_code is None:
            wx.CallLater(2000, self.monitor)
        else:
            if return_code == 0:
                self.show_message("Import complete")
            else:
                self.show_message("Import process exited with return code %d" % return_code)
            self.current_process = None
            self.button_import.Enable()


def main():
    app = wx.App()
    frame = MyFrameImpl(None)
    frame .Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
