from __future__ import annotations

import csv
import json

from tidal_utils.compare import LibraryDiff, PlaylistDiff
from tidal_utils.models import TrackSnapshot
from tidal_utils.report import format_text, write_report


def test_reports_support_all_formats(tmp_path):
    track = TrackSnapshot("1", "Song", ("Artist",))
    diff = LibraryDiff(removed_tracks=(track,), playlist_changes=(PlaylistDiff("p", "List", order_changed=True),))
    text = format_text(diff)
    assert "Removed tracks" in text
    assert "Track order changed" in text

    json_path = write_report(diff, tmp_path / "diff.json")
    assert json.loads(json_path.read_text())["removed_tracks"][0]["title"] == "Song"

    csv_path = write_report(diff, tmp_path / "diff.csv")
    with csv_path.open() as handle:
        rows = list(csv.DictReader(handle))
    assert any(row["title"] == "Song" for row in rows)

    html_path = write_report(diff, tmp_path / "diff.html")
    assert "<!doctype html>" in html_path.read_text()
