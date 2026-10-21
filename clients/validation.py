"""Strict Pydantic schemas of external API responses.

Any mismatch (missing field, wrong type, out-of-range value, NaN) is turned
into InvalidResponseError with the name of the broken field.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from clients.exceptions import InvalidResponseError


class _StrictModel(BaseModel):
    # strict: a string such as "83.9" is not accepted where a number is expected
    model_config = ConfigDict(strict=True, extra="ignore")


class GeoPlace(_StrictModel):
    name: str
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class GeocodingResponse(_StrictModel):
    # The key is absent when no place matches the query
    results: list[GeoPlace] | None = None


class CurrentWeather(_StrictModel):
    temperature_2m: float = Field(ge=-100, le=70, allow_inf_nan=False)
    weather_code: int = Field(ge=0, le=99)


class ForecastResponse(_StrictModel):
    current: CurrentWeather


class RateResponse(_StrictModel):
    base: str
    quote: str
    rate: float = Field(gt=0, allow_inf_nan=False)


def validate_payload[ModelT: BaseModel](
    model: type[ModelT], payload: Any, source: str
) -> ModelT:
    """Validate the body against the schema or raise InvalidResponseError."""
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(part) for part in first["loc"]) or "<root>"
        raise InvalidResponseError(
            f"{source}: некорректное поле {field!r}: {first['msg']}"
        ) from exc
