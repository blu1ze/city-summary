"""Open-Meteo client: geocode a city, then fetch its current weather."""

from typing import Final, TypedDict

from clients.exceptions import CityNotFoundError
from clients.http import get_json
from clients.validation import ForecastResponse, GeocodingResponse, validate_payload

GEOCODING_URL: Final = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL: Final = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes used by Open-Meteo
WMO_DESCRIPTIONS: Final[dict[int, str]] = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


class WeatherData(TypedDict):
    city: str
    temp_c: float
    description: str  # empty string for an unknown WMO code


def get_weather(city: str) -> WeatherData:
    """Return the current weather in the city or raise CityNotFoundError."""
    # Step 1: city name -> coordinates
    geo_payload = get_json(GEOCODING_URL, {"name": city, "count": 1, "language": "en"})
    geo = validate_payload(GeocodingResponse, geo_payload, "Open-Meteo geocoding")
    if not geo.results:
        raise CityNotFoundError(city)
    place = geo.results[0]

    # Step 2: coordinates -> current weather
    forecast_payload = get_json(
        FORECAST_URL,
        {
            "latitude": place.latitude,
            "longitude": place.longitude,
            "current": "temperature_2m,weather_code",
        },
    )
    forecast = validate_payload(
        ForecastResponse, forecast_payload, "Open-Meteo forecast"
    )
    current = forecast.current

    return WeatherData(
        city=place.name,
        temp_c=current.temperature_2m,
        description=WMO_DESCRIPTIONS.get(current.weather_code, ""),
    )
