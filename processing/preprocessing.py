"""Preprocessing rules applied to the data received from the clients.

The functions are pure: no network, no printing, so they are easy to test.
Flags are computed on already rounded values to keep the output consistent:
-0.04 C is shown as 0.0 C, so warm clothes are not needed for it.
"""

from typing import Final, TypedDict

WARM_CLOTHES_BELOW_C: Final = 0.0
EXPENSIVE_ABOVE_RUB: Final = 100.0
DEFAULT_DESCRIPTION: Final = "нет данных"
SMALL_RATE_SIGNIFICANT_DIGITS: Final = 4


class WeatherSummary(TypedDict):
    temp_c: float
    description: str
    warm_clothes: bool


class RateSummary(TypedDict):
    currency: str
    rate_to_rub: float
    expensive: bool


def round_temperature(temp_c: float) -> float:
    """Round to 1 decimal place; adding 0.0 turns -0.0 into 0.0."""
    return round(temp_c, 1) + 0.0


def round_rate(rate: float) -> float:
    """Rate >= 1 keeps kopecks (2 decimals), rate < 1 keeps 4 significant digits."""
    if rate >= 1:
        return round(rate, 2)
    return float(f"{rate:.{SMALL_RATE_SIGNIFICANT_DIGITS}g}")


def preprocess_weather(temp_c: float, description: str) -> WeatherSummary:
    rounded = round_temperature(temp_c)
    return WeatherSummary(
        temp_c=rounded,
        # An empty description means an unknown WMO code
        description=description or DEFAULT_DESCRIPTION,
        warm_clothes=rounded < WARM_CLOTHES_BELOW_C,
    )


def preprocess_rate(currency: str, rate: float) -> RateSummary:
    rounded = round_rate(rate)
    return RateSummary(
        currency=currency,
        rate_to_rub=rounded,
        expensive=rounded > EXPENSIVE_ABOVE_RUB,
    )
