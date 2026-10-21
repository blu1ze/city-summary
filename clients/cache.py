"""File TTL cache of numbers.

The CLI process lives a fraction of a second, so a cache in memory is useless:
we keep a JSON file on disk. Any cache error is only logged, a request must
never fail because of the cache.
"""

import contextlib
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final

import structlog
from pydantic import BaseModel, TypeAdapter, ValidationError

log = structlog.get_logger(__name__)

CACHE_DIR_ENV: Final = "CITY_SUMMARY_CACHE_DIR"


class _Entry(BaseModel):
    value: float
    stored_at: float


_CacheData = TypeAdapter(dict[str, _Entry])


def default_cache_dir() -> Path:
    """Cache directory: env variable, else XDG cache dir, else ~/.cache."""
    custom = os.environ.get(CACHE_DIR_ENV)
    if custom:
        return Path(custom)
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "city_summary"


class FileTTLCache:
    def __init__(
        self,
        path: Path,
        ttl_seconds: float,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.path = path
        self._ttl = ttl_seconds
        # The clock is a parameter, so a test can pass a fake one
        self._clock = clock

    def get(self, key: str) -> float | None:
        """Return the stored value or None if it is absent or too old."""
        entry = self._load().get(key)
        if entry is None:
            return None
        age = self._clock() - entry.stored_at
        if not 0 <= age < self._ttl:
            return None
        return entry.value

    def set(self, key: str, value: float) -> None:
        data = self._load()
        data[key] = _Entry(value=value, stored_at=self._clock())
        tmp = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(_CacheData.dump_json(data))
            tmp.replace(self.path)  # atomic replace
        except OSError as exc:
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)
            log.warning("cache_write_failed", path=str(self.path), error=str(exc))

    def _load(self) -> dict[str, _Entry]:
        try:
            return _CacheData.validate_json(self.path.read_bytes())
        except FileNotFoundError:
            return {}
        except (OSError, ValidationError) as exc:
            log.warning("cache_read_failed", path=str(self.path), error=str(exc))
            return {}
