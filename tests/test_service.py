"""Tests of the summary builder: the clients are mocked."""

from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest

from clients.exceptions import CityNotFoundError
from clients.weather import WeatherData
from processing.service import build_city_summary


@pytest.fixture
def mock_weather() -> Iterator[Mock]:
    weather = WeatherData(city="Moscow", temp_c=-3.24, description="clear sky")
    with patch("processing.service.get_weather", return_value=weather) as mock:
        yield mock


@pytest.fixture
def mock_rate() -> Iterator[Mock]:
    with patch("processing.service.get_rate", return_value=92.8512) as mock:
        yield mock


def test_builds_summary(mock_weather: Mock, mock_rate: Mock) -> None:
    summary = build_city_summary("moscow", "eur")

    assert summary == {
        "city": "Moscow",
        "weather": {
            "temp_c": -3.2,
            "description": "clear sky",
            "warm_clothes": True,
        },
        "rates": {"currency": "EUR", "rate_to_rub": 92.85, "expensive": False},
    }


def test_default_currency_is_usd_and_cache_is_on(
    mock_weather: Mock, mock_rate: Mock
) -> None:
    build_city_summary("moscow")

    mock_rate.assert_called_once_with("USD", True)


def test_cache_flag_is_passed_to_rate_client(
    mock_weather: Mock, mock_rate: Mock
) -> None:
    build_city_summary("moscow", "USD", use_cache=False)

    mock_rate.assert_called_once_with("USD", False)


def test_city_not_found_stops_before_rate(mock_weather: Mock, mock_rate: Mock) -> None:
    mock_weather.side_effect = CityNotFoundError("Qwzxzzxq")

    with pytest.raises(CityNotFoundError):
        build_city_summary("Qwzxzzxq")

    mock_rate.assert_not_called()
