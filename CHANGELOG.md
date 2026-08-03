# Changelog

## 0.2.0 - 2026-08-03

### Added

- Installable `tidal-utils` CLI with backup, compare, migrate, scan, repair, and restore commands.
- Versioned, human-readable JSON backups with atomic writes and optional retention.
- Text, JSON, CSV, and HTML comparison reports.
- Safe repair and restore previews, confidence scores, retries, interactive candidate selection, and operation logs.
- Detection of additions, removals, duplicate-count changes, playlist reordering, deleted playlists, and unavailable playlist entries.
- Automated tests and GitHub Actions CI.

### Fixed

- Album comparison now returns removed albums and handles empty new libraries.
- Album sorting no longer references a nonexistent `album.album` property.
- Playlist tracks are mapped by playlist identity rather than fragile list indexes.
- Parenthetical parsing returns a flat list and handles multiple groups non-greedily.
- Empty search results no longer cause `max()` errors.

### Security

- Pickle loading now requires explicit opt-in and is intended only for migrating trusted legacy backups.
