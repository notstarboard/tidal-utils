# tidal-utils

`tidal-utils` backs up a TIDAL collection, compares snapshots, finds unavailable content, previews safe replacements, and restores missing favorites or playlist entries.

The project uses the unofficial [`tidalapi`](https://github.com/tamland/python-tidal) client. TIDAL can change private APIs or metadata without notice, so review every repair or restore preview before applying it.

## Highlights

- Versioned, human-readable JSON backups instead of fragile Python object pickles
- Correct handling of empty libraries, duplicates, reordered playlists, and deleted playlists
- Text, JSON, CSV, and HTML diff reports
- Repair and restore commands that are dry-run by default
- Match confidence, optional fuzzy matching, interactive selection, retries, and operation logs
- Legacy script entry points and trusted-pickle migration
- Automated tests and CI across supported Python versions

## Install

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install .
```

For development:

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

The first command that connects to TIDAL creates or refreshes `tidal-session-oauth.json` through `tidalapi`. The session file and generated backups are ignored by Git.

## Commands

### Back up the library

```bash
tidal-utils backup
```

Choose an output folder and retain only the newest ten generated backups:

```bash
tidal-utils backup --output-dir backups --retain 10
```

Backups use a versioned JSON structure with tracks, albums, and each playlist's own ordered track list. Writes are atomic, so an interrupted process does not leave a half-written destination file.

### Compare backups

```bash
tidal-utils compare backups/old.json backups/new.json
```

Omit the second path to create a fresh backup before comparing:

```bash
tidal-utils compare backups/old.json
```

Write a report:

```bash
tidal-utils compare old.json new.json --report diff.html
tidal-utils compare old.json new.json --report diff.csv
tidal-utils compare old.json new.json --format json
```

The comparison detects:

- Added and removed favorite tracks and albums
- Duplicate-count changes
- Added and removed playlists
- Added and removed playlist tracks
- Playlist order changes
- Entries that became unavailable

The command exits with status `1` when differences are found, which makes it useful in scheduled jobs.

### Migrate a legacy pickle

Pickle can execute code while loading. Only migrate a backup you created and trust.

```bash
tidal-utils migrate library_backup_old.pkl library_backup_old.json
```

The `compare` and `restore` commands also accept `--allow-unsafe-pickle` for trusted legacy files.

### Scan unavailable items

```bash
tidal-utils scan
tidal-utils scan --json
```

### Preview and repair unavailable items

A repair is always a preview unless `--apply` is explicitly supplied:

```bash
tidal-utils repair
tidal-utils repair --fuzzy --min-confidence 0.65
tidal-utils repair --fuzzy --interactive
tidal-utils repair --fuzzy --apply
```

The preview shows the original item, proposed replacement, confidence, and match reasons. Applied repairs write a timestamped JSON operation log. A replacement is added before the unavailable item is removed; failures are recorded rather than silently ignored.

`--interactive` lets you choose among the highest-ranked candidates when no candidate meets the threshold or top candidates tie.

### Preview and restore a backup

Restore missing favorite tracks and albums:

```bash
tidal-utils restore backups/library.json
```

Include playlists, preserving duplicate entries and positions where possible:

```bash
tidal-utils restore backups/library.json --include-playlists
```

Apply the displayed plan:

```bash
tidal-utils restore backups/library.json --include-playlists --apply
```

Restore uses saved TIDAL IDs. An item may fail if TIDAL has retired that exact ID; the result is recorded in the restore log.

## Compatibility scripts

The original entry points remain available:

```bash
python backup.py
python compare_backups.py old.json new.json
python fix_unavailable.py -f       # preview
python fix_unavailable.py -f -r    # apply
```

New integrations should prefer the `tidal-utils` command and imports under `tidal_utils`.

## Backup format

A shortened example:

```json
{
  "format_version": 1,
  "created_at": "2026-08-03T16:00:00+00:00",
  "tracks": [
    {
      "id": "123",
      "title": "Track",
      "artists": ["Artist"],
      "album": "Album",
      "available": true,
      "explicit": false,
      "audio_quality": "HI_RES_LOSSLESS",
      "isrc": "USABC1234567"
    }
  ],
  "albums": [],
  "playlists": [
    {
      "id": "playlist-id",
      "title": "Favorites",
      "description": "",
      "tracks": []
    }
  ]
}
```

The `format_version` field allows future migrations without relying on serialized `tidalapi` classes.

## Safety notes

- Back up before applying repairs or restores.
- Inspect previews and confidence values.
- Use fuzzy matching carefully around live, acoustic, remix, edit, instrumental, and alternate-version metadata.
- Never open an untrusted pickle backup.
- Operation logs document attempted changes, but they are not a guaranteed automatic undo mechanism because TIDAL IDs can disappear.

## License

MIT
