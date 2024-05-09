# A quick and dirty way to back up your Python library to a file
#
from pathlib import Path
import pickle
import tidalapi


def log_in():
    session_file1 = Path("tidal-session-oauth.json")
    session = tidalapi.Session()
    session.login_session_file(session_file1)
    return session


def back_up(session, filename):
    tracks = session.user.favorites.tracks(limit=9999)
    albums = session.user.favorites.albums(limit=9999)
    playlists = session.user.playlists()
    with open(filename, 'wb') as backup_file:
        pickle.dump(tracks, backup_file)
        pickle.dump(albums, backup_file)
        pickle.dump(playlists, backup_file)


def load_backup(filename):
    with open(filename, 'rb') as backup_file:
        tracks = pickle.load(backup_file)
        albums = pickle.load(backup_file)
        playlists = pickle.load(backup_file)
    return tracks, albums, playlists


def main():
    session = log_in()
    backup_name = 'library_backup.pkl'
    back_up(session, backup_name)


if __name__ == '__main__':
    main()
