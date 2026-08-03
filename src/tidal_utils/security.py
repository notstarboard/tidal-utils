from __future__ import annotations

import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any

MAX_BACKUP_BYTES = 64 * 1024 * 1024

_ANSI_ESCAPE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_AUTHORIZATION = re.compile(r"(?i)\bauthorization\s*[:=]\s*(?:bearer\s+)?[^\s,;]+")
_JSON_SECRET = re.compile(
    r"(?i)([\"\'](?:access[_-]?token|refresh[_-]?token|client[_-]?secret|password|token)[\"\']\s*:\s*[\"\'])([^\"\']+)"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(authorization|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|token)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_SECRET_QUERY = re.compile(
    r"(?i)([?&](?:access[_-]?token|refresh[_-]?token|client[_-]?secret|password|token|key)=)"
    r"([^&#\s]+)"
)


def safe_display(value: Any) -> str:
    """Render untrusted metadata without terminal control sequences."""
    text = _ANSI_ESCAPE.sub("", str(value))
    return "".join(
        " " if char in "\r\n" else char
        for char in text
        if char == "\t" or (ord(char) >= 32 and not 127 <= ord(char) <= 159)
    )


def redact_sensitive(value: Any) -> str:
    """Remove common credential values and terminal controls from diagnostics."""
    text = safe_display(value)
    text = _AUTHORIZATION.sub("Authorization: [REDACTED]", text)
    text = _JSON_SECRET.sub(lambda match: f"{match.group(1)}[REDACTED]", text)
    text = _SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text)
    return _SECRET_QUERY.sub(lambda match: f"{match.group(1)}[REDACTED]", text)


def csv_safe(value: Any) -> str:
    """Prevent spreadsheet formula execution when opening generated CSV files."""
    text = safe_display(value)
    candidate = text.lstrip(" \t\r\n")
    if candidate and candidate[0] in ("=", "+", "-", "@"):
        return "'" + text
    return text


def secure_read_bytes(
    path: str | Path,
    *,
    label: str = "file",
    max_bytes: int | None = None,
) -> tuple[Path, bytes]:
    """Read one regular file without following a final-component symlink."""
    candidate = Path(path).expanduser()
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(candidate, flags)
    except FileNotFoundError:
        raise ValueError(f"{label.capitalize()} does not exist: {candidate}") from None
    except OSError as exc:
        if candidate.is_symlink():
            raise ValueError(f"Refusing to use a symbolic link as the {label}: {candidate}") from None
        raise ValueError(f"Could not open {label}: {candidate}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{label.capitalize()} must be a regular file: {candidate}")
        if max_bytes is not None and metadata.st_size > max_bytes:
            raise ValueError(
                f"{label.capitalize()} is too large ({metadata.st_size} bytes); the limit is {max_bytes} bytes."
            )
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(None if max_bytes is None else max_bytes + 1)
        if max_bytes is not None and len(data) > max_bytes:
            raise ValueError(f"{label.capitalize()} exceeds the {max_bytes}-byte limit.")
        return candidate, data
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def validate_regular_file(path: str | Path, *, label: str = "file", allow_missing: bool = False) -> Path:
    candidate = Path(path).expanduser()
    try:
        metadata = candidate.lstat()
    except FileNotFoundError:
        if allow_missing:
            return candidate
        raise ValueError(f"{label.capitalize()} does not exist: {candidate}") from None
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError(f"Refusing to use a symbolic link as the {label}: {candidate}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{label.capitalize()} must be a regular file: {candidate}")
    return candidate


def secure_session_path(path: str | Path, *, allow_missing: bool = True) -> Path:
    candidate = validate_regular_file(path, label="session file", allow_missing=allow_missing)
    if candidate.exists() and os.name == "posix":
        try:
            candidate.chmod(0o600)
        except OSError as exc:
            raise ValueError(f"Could not restrict session-file permissions: {candidate}") from exc
    return candidate


def secure_write_text(path: str | Path, content: str, *, encoding: str = "utf-8") -> Path:
    """Atomically write private data with owner-only permissions on POSIX."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding=encoding, newline="") as handle:
            descriptor = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        if os.name == "posix":
            destination.chmod(0o600)
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
        raise
    return destination
