"""Tests of the Frankfurter client: get_json is mocked, no network."""

from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest

from clients.exceptions import (
    CurrencyNotFoundError,
    InvalidResponseError,
    UpstreamHTTPError,
)
from clients.rates import get_rate


@pytest.fixture
def mock_get_json() -> Iterator[Mock]:
    with patch("clients.rates.get_json") as mock:
        yield mock


def payload(
    base: str = "USD", rate: object = 82.71, quote: str = "RUB"
) -> dict[str, object]:
    return {"date": "2026-10-21", "base": base, "quote": quote, "rate": rate}


def test_returns_rate_for_upper_cased_code(mock_get_json: Mock) -> None:
    mock_get_json.return_value = payload()

    assert get_rate("usd", use_cache=False) == 82.71

    mock_get_json.assert_called_once_with("https://api.frankfurter.dev/v2/rate/USD/RUB")


@pytest.mark.parametrize("status", [404, 422])
def test_unknown_currency_becomes_not_found(mock_get_json: Mock, status: int) -> None:
    mock_get_json.side_effect = UpstreamHTTPError("url", status, "")

    with pytest.raises(CurrencyNotFoundError):
        get_rate("XYZ", use_cache=False)


def test_other_http_errors_are_propagated(mock_get_json: Mock) -> None:
    mock_get_json.side_effect = UpstreamHTTPError("url", 400, "")

    with pytest.raises(UpstreamHTTPError):
        get_rate("USD", use_cache=False)


def test_wrong_currency_pair_is_rejected(mock_get_json: Mock) -> None:
    mock_get_json.return_value = payload(base="EUR")

    with pytest.raises(InvalidResponseError, match="ожидалась пара"):
        get_rate("USD", use_cache=False)


@pytest.mark.parametrize("bad_rate", ["83.9", 0, -1, float("nan"), None])
def test_invalid_rate_is_rejected(mock_get_json: Mock, bad_rate: object) -> None:
    mock_get_json.return_value = payload(rate=bad_rate)

    with pytest.raises(InvalidResponseError, match="rate"):
        get_rate("USD", use_cache=False)


def test_cached_rate_avoids_second_request(mock_get_json: Mock) -> None:
    mock_get_json.return_value = payload()

    assert get_rate("USD") == 82.71
    assert get_rate("USD") == 82.71

    assert mock_get_json.call_count == 1


def test_no_cache_always_requests(mock_get_json: Mock) -> None:
    mock_get_json.return_value = payload()

    get_rate("USD", use_cache=False)
    get_rate("USD", use_cache=False)

    assert mock_get_json.call_count == 2


def test_failed_request_is_not_cached(mock_get_json: Mock) -> None:
    mock_get_json.side_effect = [UpstreamHTTPError("url", 404, ""), payload()]

    with pytest.raises(CurrencyNotFoundError):
        get_rate("USD")
    assert get_rate("USD") == 82.71

    assert mock_get_json.call_count == 2
