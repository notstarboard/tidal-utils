# === backup.py ===
# A quick and dirty way to back up your Python library to a file

from fix_unavailable import log_in
from datetime import datetime
import pickle


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
    date_suffix = datetime.today().strftime('%Y-%m-%d_%H%M%S')
    backup_name = 'library_backup_' + date_suffix + '.pkl'
    back_up(session, backup_name)


if __name__ == '__main__':
    main()
