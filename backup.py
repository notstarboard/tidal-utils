"""Compatibility wrapper for the historic backup.py entry point."""

from __future__ import annotations

from tidal_utils.backup import create_backup, load_backup, save_backup, snapshot_from_session
from tidal_utils.client import log_in

__all__ = ["back_up", "create_backup", "load_backup", "log_in", "main", "save_backup", "snapshot_from_session"]


def back_up(session, filename):
    """Create a JSON backup at *filename* using the legacy function name."""
    return save_backup(snapshot_from_session(session), filename)


def main() -> None:
    path = create_backup(log_in())
    print(path)


if __name__ == "__main__":
    main()
