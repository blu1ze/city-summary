"""Frankfurter client: the rate of a currency against the Russian ruble."""

from typing import Final

import structlog

from clients.cache import FileTTLCache, default_cache_dir
from clients.exceptions import (
    CurrencyNotFoundError,
    InvalidResponseError,
    UpstreamHTTPError,
)
from clients.http import get_json
from clients.validation import RateResponse, validate_payload

log = structlog.get_logger(__name__)

RATE_URL: Final = "https://api.frankfurter.dev/v2/rate/{currency}/RUB"
QUOTE_CURRENCY: Final = "RUB"
NOT_FOUND_STATUSES: Final = frozenset({404, 422})
CACHE_TTL_SECONDS: Final = 5 * 60
CACHE_FILE_NAME: Final = "rates.json"


def get_rate(currency: str, use_cache: bool = True) -> float:
    """Return how many rubles one unit of the currency costs.

    The rate is cached on disk for 5 minutes unless use_cache is False.
    """
    code = currency.upper()

    cache: FileTTLCache | None = None
    if use_cache:
        cache = FileTTLCache(default_cache_dir() / CACHE_FILE_NAME, CACHE_TTL_SECONDS)
        cached = cache.get(code)
        if cached is not None:
            log.debug("rate_cache_hit", currency=code)
            return cached

    try:
        payload = get_json(RATE_URL.format(currency=code))
    except UpstreamHTTPError as exc:
        # Frankfurter answers 404/422 for an unknown currency code
        if exc.status_code in NOT_FOUND_STATUSES:
            raise CurrencyNotFoundError(code) from exc
        raise

    data = validate_payload(RateResponse, payload, "Frankfurter")
    # The answer must describe exactly the pair we asked for
    if data.base != code or data.quote != QUOTE_CURRENCY:
        raise InvalidResponseError(
            f"Frankfurter: ожидалась пара {code}/{QUOTE_CURRENCY}, "
            f"получена {data.base}/{data.quote}"
        )

    # Only a checked rate is stored
    if cache is not None:
        cache.set(code, data.rate)
    return data.rate
