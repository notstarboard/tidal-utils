# === fix_unavailable.py ===
# This program will identify, and optionally replace, unavailable albums and tracks in your TIDAL library.
# See README.md for key details and usage information.

import argparse
from pathlib import Path
import re
import tidalapi


def build_parser():
    parser = argparse.ArgumentParser(
        description="Identify unavailable Tracks and Albums in My Collection and attempt to replace them if desired")
    parser.add_argument("-f", help="Be more FLEXIBLE when matching metadata during replacement.",
                        action='store_true', required=False, default=False)
    parser.add_argument("-r", help="Attempt to REPLACE any unavailable Tracks and Albums in My Collection.",
                        action='store_true', required=False, default=False)
    return parser


def find_gray_albums(session):
    gray_albums = []
    albums = session.user.favorites.albums(limit=9999)
    for album in albums:
        if not album.available:
            gray_albums.append(album)
    return gray_albums


def find_gray_tracks(session):
    gray_tracks = []
    tracks = session.user.favorites.tracks(limit=9999, order="ARTIST")
    for track in tracks:
        if not track.available:
            gray_tracks.append(track)
    return gray_tracks


def find_gray_playlists(session):
    gray_playlists = []
    gray_playlist_tracks = []
    playlists = session.user.playlists()
    for playlist in playlists:
        playlist_appended = False
        playlist_tracks = playlist.tracks()
        for playlist_track in playlist_tracks:
            if not playlist_track.available:
                if not playlist_appended:
                    gray_playlists.append(playlist)
                    playlist_appended = True
                gray_playlist_tracks.append(playlist_track)
    gray_playlists.sort(key=playlist_name)
    return gray_playlists, gray_playlist_tracks


def is_fuzzy_match_album(album1, album2):
    if strip_parentheticals(album1.name.casefold()) == strip_parentheticals(album2.name.casefold()):
        fuzzy_match = True
    else:
        fuzzy_match = False
        return fuzzy_match
    sketchy_keyword = ['acoustic', 'cover', 'edit)', 'edit]', 'instrumental', 'live', ' mix', 'rediscovered',
                       'redux', 'reimagined', 're-imagined', 'reprise', 'stripped']
    for sk in sketchy_keyword:
        in_album1 = in_album2 = False
        for album1_p in parentheticals(album1.name.casefold()):
            if sk in album1_p:
                in_album1 = True
        for album2_p in parentheticals(album2.name.casefold()):
            if sk in album2_p:
                in_album2 = True
        if in_album1 != in_album2:
            fuzzy_match = False
            break
    return fuzzy_match


def is_fuzzy_match_artist(gray_obj, search_obj):
    search_artists = []
    for artist in search_obj.artists:
        search_artists.append(artist.name.casefold())
    if gray_obj.artist.name.casefold() in search_artists:
        return True
    else:
        return False


def is_fuzzy_match_track(track1, track2):
    if strip_parentheticals(track1.full_name.casefold()) == strip_parentheticals(track2.full_name.casefold()):
        fuzzy_match = True
    else:
        fuzzy_match = False
        return fuzzy_match
    sketchy_keyword = ['acoustic', 'cover', 'edit)', 'edit]', 'instrumental', 'live', 'mix', 'rediscovered',
                       'redux', 'reimagined', 're-imagined', 'reprise', 'stripped', 'ver.', 'version']
    for sk in sketchy_keyword:
        in_track1 = in_track2 = False
        for track1_p in parentheticals(track1.full_name.casefold()):
            if sk in track1_p:
                in_track1 = True
        for track2_p in parentheticals(track2.full_name.casefold()):
            if sk in track2_p:
                in_track2 = True
        if in_track1 != in_track2:
            fuzzy_match = False
            break
    return fuzzy_match


def is_valid(args):
    if args.p:
        print("WARNING: -p is deprecated. Running with -r is now sufficient to replace songs in playlists")
    if args.f and not args.r:
        print("WARNING: -f will be ignored since -r was not provided")
    return True


def log_in():
    session_file1 = Path("tidal-session-oauth.json")
    session = tidalapi.Session()
    session.login_session_file(session_file1)
    return session


def parentheticals(string):
    all_p = []
    some_p = re.findall(r'\(.*?\)', string)
    if some_p:
        all_p.append(some_p)
    some_p = re.findall(r'\[.*?\]', string)
    if some_p:
        all_p.append(some_p)
    return all_p


def playlist_name(playlist):
    return playlist.name


def print_replaced_albums(num_gray_albums, missing, new_stuck, gray_stuck):
    num_fixed_albums = num_gray_albums - len(missing) - len(new_stuck) - len(gray_stuck)
    print("-----------------------------------\n")
    print("{} of {} unavailable albums in My Collection were successfully replaced\n".format(num_fixed_albums, num_gray_albums))
    if missing:
        print("> Albums that do not appear to have an updated version on TIDAL:")
        for album in missing:
            print("{}: '{}' by '{}'".format(album.id, album.name, album.artist.name))
        print("\n")
    if new_stuck:
        print("> Albums that appear to have an updated version on TIDAL which could not be added due to an error:")
        for album in new_stuck:
            print("{}: '{}' by '{}'".format(album.id, album.name, album.artist.name))
        print("\n")
    if gray_stuck:
        print("> Tracks that had a replacement successfully added, but which could not be removed due to an error:")
        for track in gray_stuck:
            print("{}: '{}' by '{}'".format(track.id, track.full_name, track.artist.name))
        print("\n")


def print_replaced_playlists(num_gray_playlists, num_gray_playlist_tracks, missing, new_stuck, gray_stuck, imperfect_playlists):
    num_fixed_playlists = num_gray_playlists - len(imperfect_playlists)
    num_fixed_playlist_tracks = num_gray_playlist_tracks - len(missing) - len(new_stuck) - len(gray_stuck)
    print("{} of {} affected user-created playlists &".format(num_fixed_playlists, num_gray_playlists))
    print("{} of {} unavailable tracks in user-created playlists were cleaned up\n".format(num_fixed_playlist_tracks, num_gray_playlist_tracks))
    if imperfect_playlists:
        print("> Playlists that have at least one issue (read on for details):")
        for playlist in imperfect_playlists:
            print(playlist.name)
        print()
    if missing:
        print("> Tracks present in user-created playlists that do not appear to have an updated version on TIDAL:")
        for track in missing:
            print("{}: '{}' by '{}'".format(track.id, track.full_name, track.artist.name))
        print()
    if new_stuck:
        print("> Tracks present in user-created playlists that appear to have an updated version on TIDAL which could "
              + "not be added due to an error:")
        for track in new_stuck:
            print("{}: '{}' by '{}'".format(track.id, track.full_name, track.artist.name))
        print()
    if gray_stuck:
        print("> Tracks present in user-created playlists that had a replacement successfully added, but which could "
              + "not be removed due to an error:")
        for track in gray_stuck:
            print("{}: '{}' by '{}'".format(track.id, track.full_name, track.artist.name))
        print()


def print_replaced_tracks(num_gray_tracks, missing, new_stuck, gray_stuck):
    num_fixed_tracks = num_gray_tracks - len(missing) - len(new_stuck) - len(gray_stuck)
    print("{} of {} unavailable tracks in My Collection were successfully replaced\n".format(num_fixed_tracks, num_gray_tracks))
    if missing:
        print("> Tracks that do not appear to have an updated version on TIDAL:")
        for track in missing:
            print("{}: '{}' by '{}'".format(track.id, track.full_name, track.artist.name))
        print()
    if new_stuck:
        print("> Tracks that appear to have an updated version on TIDAL which could not be added due to an error:")
        for track in new_stuck:
            print("{}: '{}' by '{}'".format(track.id, track.full_name, track.artist.name))
        print()
    if gray_stuck:
        print("> Tracks that had a replacement successfully added, but which could not be removed due to an error:")
        for track in gray_stuck:
            print("{}: '{}' by '{}'".format(track.id, track.full_name, track.artist.name))
        print()


def print_gray_albums(gray_albums):
    print("Unavailable albums in My Collection:\n")
    for album in gray_albums:
        print("{}: '{}' by '{}'".format(album.id, album.name, album.artist.name))
    if not gray_albums:
        print("None")
    print()


def print_gray_playlists(gray_playlists):
    print("User-created playlists containing at least one unavailable track:\n")
    for playlist in gray_playlists:
        print(playlist.name)
    if not gray_playlists:
        print("None")
    print()


def print_gray_tracks(gray_tracks):
    print("Unavailable tracks in My Collection:\n")
    for track in gray_tracks:
        print("{}: '{}' by '{}'".format(track.id, track.full_name, track.artist.name))
    if not gray_tracks:
        print("None")
    print()


def replace_gray_albums(session, gray_albums, args):
    failed_removal = []
    missing = []
    new_stuck = []
    for gray_album in gray_albums:
        match_album = search_album(session, gray_album, args)
        if match_album:
            if session.user.favorites.add_album(match_album.id):
                if not session.user.favorites.remove_album(gray_album.id):
                    failed_removal.append(gray_album)
            else:
                new_stuck.append(gray_album)
        if not match_album:
            missing.append(gray_album)
    return missing, new_stuck, failed_removal


def replace_gray_playlists(session, gray_playlists, args):
    imperfect_playlists = []
    gray_stuck = []
    missing = []
    new_stuck = []
    for playlist in gray_playlists:
        perfect = True
        playlist_tracks = playlist.tracks()
        for i, playlist_track in enumerate(playlist_tracks):
            if not playlist_track.available:
                match_track = search_track(session, playlist_track, args)
                if match_track:
                    if playlist.add(media_ids=[match_track.id], position=i):
                        if not playlist.remove_by_id(playlist_track.id):
                            gray_stuck.append(playlist_track)
                            perfect = False
                    else:
                        new_stuck.append(playlist_track)
                        perfect = False
                else:
                    missing.append(playlist_track)
                    perfect = False
        if not perfect:
            imperfect_playlists.append(playlist)
    return missing, new_stuck, gray_stuck, imperfect_playlists


def replace_gray_tracks(session, gray_tracks, args):
    gray_stuck = []
    missing = []
    new_stuck = []
    for gray_track in gray_tracks:
        match_track = search_track(session, gray_track, args)
        if match_track:
            if session.user.favorites.add_track(match_track.id):
                if not session.user.favorites.remove_track(gray_track.id):
                    gray_stuck.append(gray_track)
            else:
                new_stuck.append(gray_track)
        else:
            missing.append(gray_track)
    return missing, new_stuck, gray_stuck


def search_album(session, gray_album, args):
    query = strip_parentheticals(gray_album.name) + " " + gray_album.artist.name
    search_albums = session.search(query=query, limit=300, models=[tidalapi.album.Album])['albums']
    score = [0] * len(search_albums)
    for i, search_album in enumerate(search_albums):
        if gray_album.name.casefold() == search_album.name.casefold() and \
                gray_album.artist.name.casefold() == search_album.artist.name.casefold():
            score[i] += 32
        elif args.f and is_fuzzy_match_album(gray_album, search_album) and is_fuzzy_match_artist(gray_album, search_album):
            score[i] += 16
            if gray_album.num_tracks == search_album.num_tracks:
                score[i] += 8
        if gray_album.explicit == search_album.explicit:
            score[i] += 4
        if gray_album.audio_quality == search_album.audio_quality:
            score[i] += 2
        gray_track = gray_album.tracks()[0]
        search_track = search_album.tracks()[0]
        if gray_track.is_DolbyAtmos == search_track.is_DolbyAtmos and gray_track.is_HiRes == search_track.is_HiRes and \
                gray_track.is_Mqa == search_track.is_Mqa and gray_track.is_Sony360RA == search_track.is_Sony360RA:
            score[i] += 1
    if max(score) >= 16:  # there must at least be a fuzzy match on artist and album to return a match
        return search_albums[score.index(max(score))]
    else:
        return None


def search_track(session, gray_track, args):
    query = strip_parentheticals(gray_track.full_name) + " " + gray_track.artist.name
    search_tracks = session.search(query=query, limit=300, models=[tidalapi.media.Track])['tracks']
    score = [0] * len(search_tracks)
    for i, search_track in enumerate(search_tracks):
        if gray_track.full_name.casefold() == search_track.full_name.casefold() and \
                gray_track.artist.name.casefold() == search_track.artist.name.casefold():
            score[i] += 64
        elif args.f and is_fuzzy_match_track(gray_track, search_track) and is_fuzzy_match_artist(gray_track, search_track):
            score[i] += 32
        if gray_track.album.name.casefold() == search_track.album.name.casefold():
            score[i] += 16
        elif args.f and is_fuzzy_match_album(gray_track.album, search_track.album):
            score[i] += 8
            if gray_track.album.num_tracks == search_track.album.num_tracks:
                score[i] += 4
        if gray_track.explicit == search_track.explicit or gray_track.album.explicit == search_track.album.explicit:
            score[i] += 2  # if clean/explicit metadata were reliable I'd rank this above album name, but it isn't
        if gray_track.audio_quality == search_track.audio_quality and \
                gray_track.is_DolbyAtmos == search_track.is_DolbyAtmos and gray_track.is_HiRes == search_track.is_HiRes and \
                gray_track.is_Mqa == search_track.is_Mqa and gray_track.is_Sony360RA == search_track.is_Sony360RA:
            score[i] += 1
    if score and max(score) >= 32:  # there must at least be a fuzzy match on artist and track to return a match
        return search_tracks[score.index(max(score))]
    else:
        return None


def strip_parentheticals(string):
    return re.sub(r'\[.*\]', '', re.sub(r'\(.*\)', '', string)).strip()


def main():
    # Read and validate the command line arguments
    parser = build_parser()
    args = parser.parse_args()
    if not is_valid(args):
        return

    # Log into Tidal
    session = log_in()

    # Identify unavailable items in My Collection
    gray_albums = find_gray_albums(session)
    print_gray_albums(gray_albums)
    gray_tracks = find_gray_tracks(session)
    print_gray_tracks(gray_tracks)
    gray_playlists, gray_playlist_tracks = find_gray_playlists(session)
    print_gray_playlists(gray_playlists)

    # Attempt to replace unavailable items if desired
    if args.r:
        missing, new_stuck, gray_stuck = replace_gray_albums(session, gray_albums, args)
        print_replaced_albums(len(gray_albums), missing, new_stuck, gray_stuck)
        missing, new_stuck, gray_stuck = replace_gray_tracks(session, gray_tracks, args)
        print_replaced_tracks(len(gray_tracks), missing, new_stuck, gray_stuck)
        imperfect_playlists, missing, new_stuck, gray_stuck = replace_gray_playlists(session, gray_playlists, args)
        print_replaced_playlists(len(gray_playlists), len(gray_playlist_tracks),
                                 missing, new_stuck, gray_stuck, imperfect_playlists)


if __name__ == '__main__':
    main()
