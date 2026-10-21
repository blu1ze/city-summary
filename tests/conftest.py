"""Shared pytest fixtures."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog


@pytest.fixture(autouse=True)
def isolated_cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the rates cache of every test away from the real home directory."""
    monkeypatch.setenv("CITY_SUMMARY_CACHE_DIR", str(tmp_path / "cache"))


@pytest.fixture(autouse=True)
def reset_structlog() -> Iterator[None]:
    """main.py reconfigures structlog; restore the defaults after each test."""
    yield
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()
