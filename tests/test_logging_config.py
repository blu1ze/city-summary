"""Tests of the logging setup."""

import re

from logging_config import configure_logging


def test_run_id_is_short_hex_and_differs_between_runs() -> None:
    first = configure_logging()
    second = configure_logging(verbose=True)

    assert re.fullmatch(r"[0-9a-f]{8}", first)
    assert first != second
