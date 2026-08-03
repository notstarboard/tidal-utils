from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, TypeVar
import logging
import time

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
    session = tidalapi.Session()
    session.login_session_file(Path(session_file))
    return session


def retry(operation: Callable[[], T], attempts: int = 3, delay: float = 0.5) -> T:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as exc:  # API clients expose several transient exception types.
            last_error = exc
            if attempt + 1 < attempts:
                wait = delay * (2**attempt)
                logger.warning("API operation failed; retrying in %.1fs: %s", wait, exc)
                time.sleep(wait)
    assert last_error is not None
    raise last_error
