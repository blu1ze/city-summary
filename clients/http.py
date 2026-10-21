"""Shared HTTP layer: one GET request with timeout, retries and JSON parsing."""

import time
from typing import Any, Final

import requests
import structlog

from clients.exceptions import (
    InvalidResponseError,
    ServiceUnavailableError,
    UpstreamHTTPError,
)

log = structlog.get_logger(__name__)

TIMEOUT_SECONDS: Final = 5.0
MAX_RETRIES: Final = 2  # retries after the first attempt, 3 attempts in total
BACKOFF_SECONDS: Final = (0.5, 1.0)  # pause before the 1st and the 2nd retry
RETRY_STATUSES: Final = frozenset({500, 502, 503, 504})
MAX_RETRY_AFTER_SECONDS: Final = 10.0
RETRYABLE_ERRORS: Final = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)

Params = dict[str, str | int | float]


def _numeric_retry_after(response: requests.Response) -> float | None:
    """Return the Retry-After header in seconds, or None if absent or not a number."""
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        # The header holds an HTTP date: we do not parse it, regular backoff is used
        return None
    return seconds if seconds >= 0 else None


def _parse_json(url: str, response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise InvalidResponseError(f"{url} вернул не JSON") from exc


def get_json(url: str, params: Params | None = None) -> Any:
    """GET the url and return the parsed JSON body.

    Retries (twice after the first attempt) on timeouts, connection errors,
    HTTP 500/502/503/504 and 429. Other 4xx statuses are not retried.
    """
    reason = "unknown"

    for attempt in range(MAX_RETRIES + 1):
        # Pause used if this attempt fails and we retry
        pause = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]

        log.debug("http_get", url=url, attempt=attempt + 1)
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
        except RETRYABLE_ERRORS as exc:
            reason = type(exc).__name__
        else:
            status = response.status_code

            if status == 429:
                reason = "HTTP 429"
                retry_after = _numeric_retry_after(response)
                if retry_after is not None:
                    if retry_after > MAX_RETRY_AFTER_SECONDS:
                        # Fail fast instead of hanging the CLI
                        raise ServiceUnavailableError(
                            f"{url} просит подождать {retry_after:g} с, "
                            "это слишком долго"
                        )
                    pause = retry_after
            elif status in RETRY_STATUSES:
                reason = f"HTTP {status}"
            elif not response.ok:
                raise UpstreamHTTPError(url, status, response.text)
            else:
                return _parse_json(url, response)

        # Here the attempt failed in a retryable way
        if attempt < MAX_RETRIES:
            log.warning(
                "http_retry", url=url, attempt=attempt + 1, reason=reason, pause=pause
            )
            time.sleep(pause)

    raise ServiceUnavailableError(
        f"{url} недоступен после {MAX_RETRIES + 1} попыток ({reason})"
    )
