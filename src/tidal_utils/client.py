from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, TypeVar
import logging
import os
import time

from .security import redact_sensitive, secure_session_path

logger = logging.getLogger(__name__)

T = TypeVar("T")


def require_tidalapi() -> Any:
    try:
        import tidalapi
    except ImportError as exc:
        raise RuntimeError(
            "tidalapi is required for commands that connect to TIDAL. "
            "Install the project with `pip install .`."
        ) from exc
    return tidalapi


def log_in(session_file: str | Path = "tidal-session-oauth.json") -> Any:
    tidalapi = require_tidalapi()
    path = secure_session_path(session_file, allow_missing=True)
    session = tidalapi.Session()
    previous_umask = os.umask(0o077) if os.name == "posix" else None
    try:
        session.login_session_file(path)
    finally:
        if previous_umask is not None:
            os.umask(previous_umask)
    if path.exists():
        secure_session_path(path, allow_missing=False)
    return session


def retry(operation: Callable[[], T], attempts: int = 3, delay: float = 0.5) -> T:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if delay < 0:
        raise ValueError("delay cannot be negative")
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as exc:  # API clients expose several transient exception types.
            last_error = exc
            if attempt + 1 < attempts:
                wait = delay * (2**attempt)
                logger.warning(
                    "API operation failed; retrying in %.1fs: %s",
                    wait,
                    redact_sensitive(exc),
                )
                time.sleep(wait)
    if last_error is None:
        raise RuntimeError("retry failed without capturing an exception")
    raise last_error
