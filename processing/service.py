"""Build the city summary: fetch data through the clients and apply the rules."""

from typing import TypedDict

from clients.rates import get_rate
from clients.weather import get_weather
from processing.preprocessing import (
    RateSummary,
    WeatherSummary,
    preprocess_rate,
    preprocess_weather,
)


class CitySummary(TypedDict):
    city: str
    weather: WeatherSummary
    rates: RateSummary


def build_city_summary(city: str, currency: str = "USD") -> CitySummary:
    """Return weather and the currency rate to the ruble for the city."""
    weather = get_weather(city)
    rate = get_rate(currency)

    return CitySummary(
        city=weather["city"],
        weather=preprocess_weather(weather["temp_c"], weather["description"]),
        rates=preprocess_rate(currency.upper(), rate),
    )
