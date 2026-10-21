"""Frankfurter client: the rate of a currency against the Russian ruble."""

from typing import Final

from clients.exceptions import (
    CurrencyNotFoundError,
    InvalidResponseError,
    UpstreamHTTPError,
)
from clients.http import get_json
from clients.validation import RateResponse, validate_payload

RATE_URL: Final = "https://api.frankfurter.dev/v2/rate/{currency}/RUB"
QUOTE_CURRENCY: Final = "RUB"
NOT_FOUND_STATUSES: Final = frozenset({404, 422})


def get_rate(currency: str) -> float:
    """Return how many rubles one unit of the currency costs."""
    code = currency.upper()
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
    return data.rate
