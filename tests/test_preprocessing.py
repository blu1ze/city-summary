"""Tests of the preprocessing rules: pure functions, nothing to mock."""

import pytest

from processing.preprocessing import (
    preprocess_rate,
    preprocess_weather,
    round_rate,
    round_temperature,
)


def test_negative_zero_is_normalised() -> None:
    assert str(round_temperature(-0.04)) == "0.0"


@pytest.mark.parametrize(
    ("temp", "expected_temp", "warm"),
    [
        (-0.04, 0.0, False),
        (-0.06, -0.1, True),
        (0.0, 0.0, False),
        (-3.24, -3.2, True),
        (7.6, 7.6, False),
    ],
)
def test_warm_clothes_uses_rounded_temperature(
    temp: float, expected_temp: float, warm: bool
) -> None:
    summary = preprocess_weather(temp, "overcast")

    assert summary["temp_c"] == expected_temp
    assert summary["warm_clothes"] is warm


def test_empty_description_gets_default() -> None:
    assert preprocess_weather(5.0, "")["description"] == "нет данных"
    assert preprocess_weather(5.0, "fog")["description"] == "fog"


@pytest.mark.parametrize(
    ("rate", "expected"),
    [
        (93.9764, 93.98),
        (1.0, 1.0),
        (1234.5678, 1234.57),
        (0.18623, 0.1862),
        (0.0456789, 0.04568),
    ],
)
def test_round_rate_precision_depends_on_magnitude(
    rate: float, expected: float
) -> None:
    assert round_rate(rate) == expected


@pytest.mark.parametrize(
    ("rate", "expected_rate", "expensive"),
    [
        (100.0, 100.0, False),
        (100.004, 100.0, False),
        (100.006, 100.01, True),
        (82.71, 82.71, False),
        (150.0, 150.0, True),
    ],
)
def test_expensive_uses_rounded_rate(
    rate: float, expected_rate: float, expensive: bool
) -> None:
    summary = preprocess_rate("EUR", rate)

    assert summary["currency"] == "EUR"
    assert summary["rate_to_rub"] == expected_rate
    assert summary["expensive"] is expensive
