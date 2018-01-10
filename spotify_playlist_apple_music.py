# coding=utf-8
import argparse
import ctypes
import json
import os
import string
import urllib2
import urlparse
# noinspection PyPackageRequirements
import bs4
import time

import pywinauto
import pywinauto.base_wrapper
import pywinauto.controls
import requests

from spamutil import Timer, dout, dlogfile
from unidecode import unidecode

script_path = os.path.dirname(os.path.abspath(__file__))

SKIP_ARTISTS = frozenset([])

SKIP_SONGS = frozenset([])

LEAVE_OUT_PHRASES = ["Remastered 2011", "Remastered", "- Acoustic", "Remaster"]

# This is to be set by the playlist loader to something appropriate for a playlist name
loaded_playlist_name = None


def fetch_cached(url, cache_filename="junkfile", ua=None):
    """ GET the given URL, using junkfile as a cache """
    cache_filename = os.path.join(script_path, cache_filename)
    if os.path.exists(cache_filename):
        return read_contents(cache_filename)

    contents = fetch(url, ua=ua)
    write_contents(cache_filename, contents)
    return contents


def write_contents(filename, contents):
    """ Write the given contents to the given file, overwriting if it already exists """
    with open(filename, "wb") as handle:
        handle.write(contents)


def fetch(url, ua=None):
    """ GET the given URL """
    if ua is None:
        req = urllib2.Request(url)
    else:
        req = urllib2.Request(url, headers={"User-Agent": ua})
    handle = urllib2.urlopen(req)
    try:
        contents = handle.read()
    finally:
        handle.close()
    return contents


def read_contents(filename):
    """ Read the contents of the given file """
    with open(filename, "rb") as handle:
        return handle.read()


def make_soup(contents):
    """ Parse the given HTML web page contents using BeautifulSoup """
    return bs4.BeautifulSoup(contents, "html.parser")


# Keycodes to pass to type_keys for characters in the search
# (characters not specified here will be used directly)
CHARACTER_CODES = {" ": "{VK_SPACE}",
                   "+": "+=",
                   "(": "+9",
                   ")": "+0",
                   }


def text_to_sendkeys_str(text):
    output_parts = []

    for ch in text:
        if ch in CHARACTER_CODES:
            output_parts.append(CHARACTER_CODES[ch])
        else:
            output_parts.append(ch)

    text = "".join(output_parts)
    return text


def type_edit_text(control, text):
    """ Enter the text into the given iTunes text box control """
    control.click_input()

    text = text_to_sendkeys_str(text)
    type_string = "^A" + text
    control.type_keys(type_string)


def firstpos(s, needle):
    """ Get the position of the first appearance of the substring needle in the string s, or None if it is not found."""
    r = s.find(needle)
    if r == -1:
        return None
    return r


def trim_punct(s):
    """ Return the part of s from the beginning up to but not including the first punctuation mark """
    positions = [firstpos(s, ch) for ch in string.punctuation]
    if any(x is not None for x in positions):
        first = min(x for x in positions if x is not None)
        s = s[:first].strip()
    return s


def ichildren(obj, **kwargs):
    """ An iterator version of BaseWrapper.children() """
    assert isinstance(obj, pywinauto.base_wrapper.BaseWrapper)

    child_elements = obj.element_info.children(**kwargs)
    for element_info in child_elements:
        child = obj.backend.generic_wrapper_class(element_info)
        assert isinstance(child, pywinauto.base_wrapper.BaseWrapper)
        yield child


def get_child_at(obj, i, **kwargs):
    """ Equivalent to doing BaseWrapper.children() and then getting a single item out of the resulting list """
    assert isinstance(obj, pywinauto.base_wrapper.BaseWrapper)
    child_elements = obj.element_info.children(**kwargs)
    element_info = child_elements[i]
    child = obj.backend.generic_wrapper_class(element_info)
    assert isinstance(child, pywinauto.base_wrapper.BaseWrapper)
    return child


# Word replacements to do in the search (to match what Apple Music does in their catalog)
WORD_REPLACEMENTS = {
    "fuck": "f**k",
    "shit": "s**t"
}


def word_replacement(s):
    words = s.split(" ")
    for i, word in enumerate(words[1:], start=1):
        if word.lower() == "featuring":
            words = words[:i]
            break

    return " ".join(WORD_REPLACEMENTS.get(word.lower(), word) for word in words)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("url",
                        help="An open.spotify.com URL for the public playlist to import")
    parser.add_argument("--playlist-name",
                        help="The name of the iTunes playlist to create or add to. (default: use the name from the spotify playlist)")
    parser.add_argument("--create",
                        help="Create the playlist instead of expecting it to exist",
                        default=False,
                        action="store_true"
                        )
    return parser.parse_args()


VK_SCROLL = 0x91


def scroll_lock_on():
    """ Check if the keyboard Scroll Lock is turned on"""
    hll_dll = ctypes.WinDLL("User32.dll")
    out = hll_dll.GetKeyState(VK_SCROLL)
    return out


def unilower(s):
    """ Lower-case a string and convert accented characters to unaccented equivalents for matching """
    return unidecode(s.lower())


def main():
    options = parse_args()

    dlogfile(os.path.join(script_path, "output.log"))

    dout("iTunes automation. Turn on SCROLL LOCK to stop before the next track.")
    assert not scroll_lock_on()

    url = options.url

    skip_to_filename_static = os.path.join(script_path, "skip_to.txt")
    skip_to_filename_hash = os.path.join(script_path, "skip_to_%s.txt" % hash(url))

    for skip_to_filename in [skip_to_filename_hash, skip_to_filename_static]:
        if os.path.exists(skip_to_filename):
            skip_to = read_contents(skip_to_filename).decode('utf-8').strip()
            break
    else:
        skip_to = None

    do_create = options.create and skip_to is None
    if options.create and skip_to is not None:
        dout("Note: --create specified but not creating a playlist because skip_to track is present which indicates playlist should already exist")

    no_results_filename = os.path.join(script_path, "no_results.log")

    # pywinauto.application.Application(backend="uia").start(r"c:\Program Files\iTunes\iTunes.exe")
    app = pywinauto.application.Application(backend="uia").connect(path="itunes.exe")

    win = app.window(title="iTunes")

    desktop = pywinauto.Desktop(backend='uia')

    window = win.wrapper_object()
    assert isinstance(window, pywinauto.controls.uiawrapper.UIAWrapper)
    window.set_focus()
    if True:

        parsed_url = urlparse.urlparse(url)

        track_source = TRACK_SOURCES[parsed_url.hostname]
        tracks = track_source(url)

        started = False
        if skip_to is None:
            started = True

        # dialog = win.child_window(title="iTunes", control_type="Window")

        time.sleep(0.25)

        search, _ = uia_find_first_child(window, "Search", "Edit")

        assert isinstance(search, pywinauto.base_wrapper.BaseWrapper)

        verify_context_menu = True

        for input_track_num, track in enumerate(tracks):
            if scroll_lock_on():
                assert False, "stopping - scroll lock on"

            playlist_name = options.playlist_name
            if playlist_name is None:
                playlist_name = loaded_playlist_name
            assert playlist_name is not None

            original_track_name = track["name"]
            original_track_artist = track["artist"]
            what_to_search_for = original_track_name + " " + original_track_artist
            if not started:
                if what_to_search_for.lower().startswith(skip_to.lower()):
                    started = True
                else:
                    dout((input_track_num, what_to_search_for))
                    continue
            else:
                write_contents(skip_to_filename_hash, what_to_search_for.encode("utf-8"))

            if original_track_artist in SKIP_ARTISTS:
                continue
            if what_to_search_for.lower() in SKIP_SONGS:
                continue

            for lop in LEAVE_OUT_PHRASES:
                if lop in what_to_search_for:
                    what_to_search_for = what_to_search_for.replace(lop, "")
                what_to_search_for = " ".join(what_to_search_for.split())

            what_to_search_for = what_to_search_for.lower()

            dout("%d. %s" % (input_track_num + 1, what_to_search_for))

            try:
                type_edit_text(search, what_to_search_for)
            except pywinauto.findwindows.ElementAmbiguousError:
                win.print_control_identifiers()
                raise

            time.sleep(0.25)

            search.type_keys("{VK_RETURN}")

            results_poll_time = 1

            # Wait for the results label to indicate that the results for our search are now on-screen
            expected_results_label_text = (u"Showing Results for “ %s ” in Apple Music" % what_to_search_for)
            failure_result_label_text = (u"No results for “%s”" % what_to_search_for)
            dout("Want label text: %r" % expected_results_label_text)
            dout("Error label text: %r" % failure_result_label_text)

            found = False

            for i in xrange(10):
                time.sleep(results_poll_time)

                _, search_custom_idx = uia_find_first_descendent_depth_first(window, "Search", "Custom")
                if search_custom_idx is not None:
                    try:
                        expected_results_label = uia_fetch(window, uia_sibling(search_custom_idx))
                    except IndexError:
                        # go around
                        continue
                    if expected_results_label is not None:
                        actual_label_text = expected_results_label.texts()[0]
                        dout("Got label text: %r" % actual_label_text)
                        if actual_label_text == expected_results_label_text:
                            found = True
                            break
                        elif actual_label_text == "":
                            child = uia_fetch(expected_results_label, [0])
                            actual_label_text = child.texts()[0]
                            if actual_label_text == failure_result_label_text:
                                break
            else:
                dout(tree_uia(window))
                assert False, "Results never loaded"

            time.sleep(0.25)

            if not found:
                with open(no_results_filename, "a") as handle:
                    print >> handle, (u"%s - %s - %s - %s" % ((input_track_num + 1), original_track_name, original_track_artist, actual_label_text)).encode('utf-8')
                continue

            songs_label, songs_label_idx = uia_find_first_descendent_depth_first(window, "SONGS", "Custom")

            dout((songs_label, songs_label_idx))

            # dout(uia_fetch(window, songs_label_idx))

            for _ in xrange(4):
                songs_group_idx = uia_sibling(songs_label_idx, 1)
                try:
                    songs_group = uia_fetch(window, songs_group_idx)
                except IndexError:
                    time.sleep(0.5)
                break
            else:
                assert False, "error finding songs list"

            if uia_fetch(songs_group, [0]).texts()[0] == "See All":
                songs_group_idx = uia_sibling(songs_label_idx, 2)
                songs_group = uia_fetch(window, songs_group_idx)

            # The songs group is a list of what seems to be a set number of entries for each song concatenated together
            songs_group_size = 5

            songs_group_children = songs_group.children()
            try:
                assert len(songs_group_children) % songs_group_size == 0, "songs group has %d entries which is not an expected multiple" % len(songs_group_children)
            except:
                dout(tree_uia(uia_fetch(window, songs_label_idx[:-1])))
                raise

            # go through the songs

            songs_seen = []

            for i in xrange(0, len(songs_group_children), songs_group_size):
                label_box = songs_group_children[i + 2]
                assert isinstance(label_box, pywinauto.controls.uiawrapper.UIAWrapper)
                title_group, album_group = [uia_fetch(group, [0, 0]) for group in label_box.children()]
                assert isinstance(title_group, pywinauto.controls.uia_controls.EditWrapper)
                assert isinstance(album_group, pywinauto.controls.uia_controls.EditWrapper)
                found_song_title = title_group.texts()[0]
                found_song_artist = album_group.texts()[0]

                song_result_num = i/songs_group_size + 1

                dout("Song result #%d: %s - %s" % (song_result_num, found_song_artist, found_song_title))

                songs_seen.append((found_song_title, found_song_artist))

                original_candidate = trim_punct(word_replacement(unilower(original_track_name)))
                found_candidate = trim_punct(unilower(found_song_title))
                if original_candidate not in found_candidate:
                    dout("Original song %r (%r) doesn't match %r (%r)" % (original_track_name, original_candidate, found_song_title, found_candidate))
                    continue
                found_artist_candidate = unilower(found_song_artist)
                original_artist_candidate = unilower(original_track_artist)
                if trim_punct(original_artist_candidate) in found_artist_candidate:
                    artist_match_on = trim_punct(original_artist_candidate)
                elif trim_punct(found_artist_candidate) in original_artist_candidate:
                    artist_match_on = trim_punct(found_artist_candidate)
                else:
                    dout("Original song artist %r (%r) doesn't match %r (%r)" % (original_track_artist, original_artist_candidate, found_song_artist, found_artist_candidate))
                    continue

                dout("Matched on %r - %r" % (artist_match_on, original_candidate))

                buttons = songs_group_children[i + 4].children()
                dots_button = buttons[-1]
                assert isinstance(dots_button, pywinauto.controls.uia_controls.ButtonWrapper)
                dots_button.click()

                if verify_context_menu:
                    time_to_context = Timer("context show")

                    time.sleep(1)

                    # context = desktop.Context.wrapper_object()
                    try:
                        context = app.Context.wrapper_object()
                    except pywinauto.findbestmatch.MatchError:
                        print app.windows()
                        raise

                    dout(time_to_context.show())

                    assert isinstance(context, pywinauto.controls.uia_controls.MenuWrapper)

                    time_to_context.show()

                    if do_create:
                        # Create a new playlist with this track from the context menu
                        playlists, _ = uia_find_first_child(context, "Add to Playlist")
                        assert playlists is not None
                        assert isinstance(playlists, pywinauto.controls.uia_controls.MenuItemWrapper)

                        playlists.expand()
                        time.sleep(0.25)
                        # select the first option from the submenu, which is new playlist option
                        context.type_keys("{VK_DOWN}{VK_RETURN}")

                        time.sleep(1)

                        dout(tree_uia(window))

                        # Playlist created from a track gets a default name "<artist> - <track>"
                        actual_text = None
                        for _ in xrange(10):
                            should_be_group_box = get_child_at(window, 0)
                            actual_text = should_be_group_box.texts()[0]
                            if actual_text.startswith(found_song_artist + " - ") and actual_text.endswith(" header"):
                                break
                            time.sleep(0.5)
                        else:
                            assert False, (actual_text, found_song_artist)

                        # We start with the playlist name in rename mode with the existing text selected
                        window.type_keys(text_to_sendkeys_str(playlist_name) + "{VK_RETURN}")

                        do_create = False

                        assert verify_context_menu
                        # We left this set because it will confirm that the playlist was created with the right name
                        # when we read the name back off the context menu when adding the next track

                    else:

                        expected_menu_item_name = "Add to Last Playlist, " + playlist_name

                        preset_playlist = get_child_at(context, 1)

                        time_to_context.show()

                        assert preset_playlist is not None
                        assert isinstance(preset_playlist, pywinauto.controls.uia_controls.MenuItemWrapper)
                        assert preset_playlist.texts()[0] == expected_menu_item_name, "Couldn't find menu item %r" % expected_menu_item_name

                        preset_playlist.select()

                        # okay, the context menu worked; from this point on use a keyboard shortcut
                        verify_context_menu = False
                else:
                    time.sleep(0.5)
                    window.type_keys("l")

                # time_to_context.stop_and_show()
                time.sleep(2)

                break
            else:
                assert False, "We didn't find the song in the results list %r" % songs_seen


def uia_sibling(l, rel=+1):
    """
    :type l: list of int
    :type rel: int
    """
    return l[:-1] + [l[-1] + rel]


def uia_fetch(obj, l):
    assert isinstance(obj, pywinauto.controls.uiawrapper.UIAWrapper)
    cur = obj
    for child_idx in l:
        cur = get_child_at(cur, child_idx)
    return cur


def uia_find_first_child(obj, title, class_name=None):
    """
    Search the direct children of a UIA control for a control with the
    given title (and optionally class name) and return
    the matching control and its index or None, None if no match was found
    :type obj: pywinauto.controls.uiawrapper.UIAWrapper
    :type title: unicode or str
    :type class_name: None or unicode or str
    :rtype: (pywinauto.controls.uiawrapper.UIAWrapper, int or None)
    """
    assert isinstance(obj, pywinauto.controls.uiawrapper.UIAWrapper)
    for i, child in enumerate(ichildren(obj)):
        assert isinstance(child, pywinauto.controls.uiawrapper.UIAWrapper)
        cur_title = child.texts()[0]
        if cur_title == title:
            if class_name is None or class_name == child.friendly_class_name():
                return child, i
    return None, None


def uia_find_first_descendent_depth_first(obj, title, class_name=None):
    """
    Search the descendents of a UIA control, in depth-first order,
    for a control with the given title (and optionally class name) and return
    the matching control and the list of indexes to get to it or None, None
    if no match was found
    :type obj: pywinauto.controls.uiawrapper.UIAWrapper
    :type title: unicode or str
    :type class_name: None or unicode or str
    :rtype: (pywinauto.controls.uiawrapper.UIAWrapper or None, list of int or None)
    """
    assert isinstance(obj, pywinauto.controls.uiawrapper.UIAWrapper)
    for i, child in enumerate(ichildren(obj)):
        assert isinstance(child, pywinauto.controls.uiawrapper.UIAWrapper)
        cur_title = child.texts()[0]
        if cur_title == title:
            if class_name is None or class_name == child.friendly_class_name():
                return child, [i]
        else:
            sub_child, sub_indices = uia_find_first_descendent_depth_first(child, title, class_name)
            if sub_child is not None:
                return sub_child, [i] + sub_indices
    return None, None


def tree_uia(obj, indent="", output_list=None):
    """ Dump the structure of the subtree of a UIA control to a string suitable for debug output """
    top = output_list is None
    if output_list is None:
        output_list = []
    output_list.append(indent + str(obj))
    subindent = indent + "   "
    for child in ichildren(obj):
        tree_uia(child, subindent, output_list)
    if top:
        return "\n".join(output_list)


def get_spotify_playlist(url):
    """
    Iterate through the tracks in the public Spotify playlist at the given
    open.spotify.com URL, caching downloaded sections to junkfile* files.
    :rtype: collections.Iterable[dict[str, unicode]]
    """

    global loaded_playlist_name

    cache_filename = "cache_spotify_%s" % hash(url)

    contents = fetch_cached(url, cache_filename=cache_filename)
    prev_url = url
    authorization = None

    soup = make_soup(contents)

    # dout(soup)

    script = soup.find_all("script")[4]
    script_text = script.get_text()

    start_marker = "Spotify.Entity = "
    end_marker = ";"

    # print repr(script_text[-5:])

    start_pos = script_text.find(start_marker)
    assert start_pos >= 0

    end_pos = script_text.rfind(end_marker)
    assert end_pos >= 0

    script_text = script_text[start_pos + len(start_marker):end_pos]

    entity = json.loads(script_text)

    tracks_obj = entity["tracks"]

    # print tracks_obj

    loaded_playlist_name = entity["name"]

    expected_offset = 0
    while True:
        seen_offset = tracks_obj["offset"]
        assert seen_offset == expected_offset, (seen_offset, expected_offset)

        for item in tracks_obj["items"]:
            track = item["track"]
            album = track["album"]["name"]
            artists = [artist["name"] for artist in track["artists"]]
            title = track["name"]

            yield {"name": title, "artist": artists[0], "album": album}

            expected_offset += 1

        next_url = tracks_obj.get("next")
        dout("next: %s" % next_url)

        if next_url is None:
            break

        cache_filename = "junkfile%d" % expected_offset

        if os.path.exists(cache_filename):
            contents = read_contents(cache_filename)
            tracks_obj = json.loads(contents)
        else:
            if authorization is None:
                authorization = read_contents(os.path.join(script_path, "spotify_authorization.txt"))
            response = requests.get(next_url, headers={"Authorization": authorization,
                                                       "Accept": "application/json",
                                                       "Origin": "https://open.spotify.com",
                                                       "Referer": prev_url})
            contents = response.text
            # print "contents: " + repr(contents)
            tracks_obj = json.loads(contents)
            # print tracks_obj
            assert tracks_obj["offset"] == expected_offset, "Got %d expected %d" % (tracks_obj["offset"], expected_offset)
            write_contents(cache_filename, contents.encode("utf-8"))

        prev_url = next_url


def get_browsery_ua():
    return read_contents(os.path.join(script_path, "user_agent.txt"))


def get_allmusic_playlist(url):
    cache_filename = "cache_allmusic_%s" % hash(url)

    contents = fetch_cached(url, cache_filename, ua=get_browsery_ua())

    soup = make_soup(contents)

    print contents
    album_title = soup.find("h1", {"class": "album-title"}).get_text().strip()

    table = soup.find("table")

    for tr in table.find_all("tr", {"class": "track"}):

        title_obj = tr.find("div", {"class": "title"})
        title = title_obj.get_text()
        title = title.strip()
        performer = tr.find("td", {"class": "performer"})
        artists = []

        for artist in performer.find_all("span", {"itemprop": "name"}):
            artists.append(artist.get_text().strip())

        out = {"name": title, "artist": artists[0], "album": album_title}
        yield out


TRACK_SOURCES = {
    "open.spotify.com": get_spotify_playlist,
    "www.allmusic.com": get_allmusic_playlist,
}


if __name__ == "__main__":
    main()
