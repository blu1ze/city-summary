"""Tests of the Open-Meteo client: get_json is mocked, no network."""

from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest

from clients.exceptions import CityNotFoundError, InvalidResponseError
from clients.weather import get_weather

GEO: dict[str, object] = {
    "results": [{"name": "Moscow", "latitude": 55.75, "longitude": 37.62}]
}


@pytest.fixture
def mock_get_json() -> Iterator[Mock]:
    with patch("clients.weather.get_json") as mock:
        yield mock


def forecast(temp: object = 7.6, code: object = 3) -> dict[str, object]:
    return {"current": {"temperature_2m": temp, "weather_code": code}}


def test_returns_weather(mock_get_json: Mock) -> None:
    mock_get_json.side_effect = [GEO, forecast()]

    weather = get_weather("moscow")

    assert weather == {"city": "Moscow", "temp_c": 7.6, "description": "overcast"}
    geocoding_params = mock_get_json.call_args_list[0].args[1]
    forecast_params = mock_get_json.call_args_list[1].args[1]
    assert geocoding_params["name"] == "moscow"
    assert forecast_params["latitude"] == 55.75


@pytest.mark.parametrize("geo", [{}, {"results": []}])
def test_unknown_city(mock_get_json: Mock, geo: dict[str, object]) -> None:
    mock_get_json.side_effect = [geo]

    with pytest.raises(CityNotFoundError):
        get_weather("Qwzxzzxq")

    assert mock_get_json.call_count == 1


def test_unknown_weather_code_gives_empty_description(mock_get_json: Mock) -> None:
    mock_get_json.side_effect = [GEO, forecast(code=98)]

    assert get_weather("Moscow")["description"] == ""


@pytest.mark.parametrize("bad_temp", [200, "7.6", float("nan"), None])
def test_invalid_temperature(mock_get_json: Mock, bad_temp: object) -> None:
    mock_get_json.side_effect = [GEO, forecast(temp=bad_temp)]

    with pytest.raises(InvalidResponseError, match="temperature_2m"):
        get_weather("Moscow")


@pytest.mark.parametrize("bad_code", [100, "3", None])
def test_invalid_weather_code(mock_get_json: Mock, bad_code: object) -> None:
    mock_get_json.side_effect = [GEO, forecast(code=bad_code)]

    with pytest.raises(InvalidResponseError, match="weather_code"):
        get_weather("Moscow")


def test_missing_current_block(mock_get_json: Mock) -> None:
    mock_get_json.side_effect = [GEO, {}]

    with pytest.raises(InvalidResponseError, match="current"):
        get_weather("Moscow")


def test_invalid_coordinates(mock_get_json: Mock) -> None:
    bad_geo = {"results": [{"name": "X", "latitude": 120, "longitude": 10}]}
    mock_get_json.side_effect = [bad_geo]

    with pytest.raises(InvalidResponseError, match="latitude"):
        get_weather("X")
