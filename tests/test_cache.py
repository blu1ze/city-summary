"""Tests of the file TTL cache: a fake clock, no real waiting."""

from pathlib import Path

import pytest

from clients.cache import CACHE_DIR_ENV, FileTTLCache, default_cache_dir


class FakeClock:
    """A clock that shows whatever time the test sets."""

    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_fresh_value_is_returned(tmp_path: Path) -> None:
    clock = FakeClock()
    cache = FileTTLCache(tmp_path / "c.json", 300, clock)
    cache.set("USD", 82.71)

    clock.now += 299

    assert cache.get("USD") == 82.71


def test_expired_value_is_not_returned(tmp_path: Path) -> None:
    clock = FakeClock()
    cache = FileTTLCache(tmp_path / "c.json", 300, clock)
    cache.set("USD", 82.71)

    clock.now += 300

    assert cache.get("USD") is None


def test_unknown_key_returns_none(tmp_path: Path) -> None:
    cache = FileTTLCache(tmp_path / "c.json", 300)
    assert cache.get("EUR") is None


def test_value_survives_a_new_instance(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    clock = FakeClock()
    FileTTLCache(path, 300, clock).set("USD", 82.71)

    assert FileTTLCache(path, 300, clock).get("USD") == 82.71


def test_clock_going_backwards_invalidates_value(tmp_path: Path) -> None:
    clock = FakeClock()
    cache = FileTTLCache(tmp_path / "c.json", 300, clock)
    cache.set("USD", 82.71)

    clock.now -= 10

    assert cache.get("USD") is None


def test_corrupted_file_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    path.write_text("not json", encoding="utf-8")

    assert FileTTLCache(path, 300).get("USD") is None


def test_write_error_does_not_raise(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")  # a file where a directory is needed
    cache = FileTTLCache(blocker / "c.json", 300)

    cache.set("USD", 82.71)  # must not raise

    assert cache.get("USD") is None


def test_default_cache_dir_uses_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(CACHE_DIR_ENV, str(tmp_path / "custom"))

    assert default_cache_dir() == tmp_path / "custom"


def test_default_cache_dir_falls_back_to_xdg(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(CACHE_DIR_ENV, raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))

    assert default_cache_dir() == tmp_path / "xdg" / "city_summary"
