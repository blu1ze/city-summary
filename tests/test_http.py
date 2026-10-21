"""Tests of the HTTP layer: requests.get and time.sleep are mocked, no network."""

from collections.abc import Iterator
from unittest.mock import Mock, call, patch

import pytest
import requests

from clients.exceptions import (
    InvalidResponseError,
    ServiceUnavailableError,
    UpstreamHTTPError,
)
from clients.http import get_json

URL = "https://example.test/api"


@pytest.fixture
def mock_get() -> Iterator[Mock]:
    with patch("clients.http.requests.get") as mock:
        yield mock


@pytest.fixture
def mock_sleep() -> Iterator[Mock]:
    with patch("clients.http.time.sleep") as mock:
        yield mock


def make_response(
    status: int = 200,
    body: object = None,
    headers: dict[str, str] | None = None,
) -> Mock:
    """A fake requests.Response."""
    response = Mock()
    response.status_code = status
    response.ok = status < 400
    response.headers = headers or {}
    response.text = "error body"
    response.json.return_value = body
    return response


def test_returns_parsed_json(mock_get: Mock, mock_sleep: Mock) -> None:
    mock_get.return_value = make_response(body={"a": 1})

    assert get_json(URL, {"q": "x"}) == {"a": 1}

    mock_get.assert_called_once_with(URL, params={"q": "x"}, timeout=5.0)
    mock_sleep.assert_not_called()


def test_retries_timeout_then_succeeds(mock_get: Mock, mock_sleep: Mock) -> None:
    mock_get.side_effect = [
        requests.exceptions.Timeout(),
        make_response(body={"ok": True}),
    ]

    assert get_json(URL) == {"ok": True}

    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(0.5)


def test_gives_up_after_three_attempts(mock_get: Mock, mock_sleep: Mock) -> None:
    mock_get.side_effect = requests.exceptions.ConnectionError()

    with pytest.raises(ServiceUnavailableError, match="3 попыток"):
        get_json(URL)

    assert mock_get.call_count == 3
    assert mock_sleep.call_args_list == [call(0.5), call(1.0)]


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_retries_server_errors(status: int, mock_get: Mock, mock_sleep: Mock) -> None:
    mock_get.side_effect = [
        make_response(status),
        make_response(status),
        make_response(body={"ok": True}),
    ]

    assert get_json(URL) == {"ok": True}

    assert mock_sleep.call_args_list == [call(0.5), call(1.0)]


def test_429_waits_numeric_retry_after(mock_get: Mock, mock_sleep: Mock) -> None:
    mock_get.side_effect = [
        make_response(429, headers={"Retry-After": "3"}),
        make_response(body={"ok": True}),
    ]

    assert get_json(URL) == {"ok": True}

    mock_sleep.assert_called_once_with(3.0)


def test_429_too_long_retry_after_fails_fast(mock_get: Mock, mock_sleep: Mock) -> None:
    mock_get.return_value = make_response(429, headers={"Retry-After": "60"})

    with pytest.raises(ServiceUnavailableError, match="слишком долго"):
        get_json(URL)

    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


def test_429_date_retry_after_uses_backoff(mock_get: Mock, mock_sleep: Mock) -> None:
    date_header = "Wed, 21 Oct 2026 07:28:00 GMT"
    mock_get.side_effect = [
        make_response(429, headers={"Retry-After": date_header}),
        make_response(body={"ok": True}),
    ]

    assert get_json(URL) == {"ok": True}

    mock_sleep.assert_called_once_with(0.5)


def test_other_client_errors_are_not_retried(mock_get: Mock, mock_sleep: Mock) -> None:
    mock_get.return_value = make_response(404)

    with pytest.raises(UpstreamHTTPError) as exc_info:
        get_json(URL)

    assert exc_info.value.status_code == 404
    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


def test_body_that_is_not_json(mock_get: Mock, mock_sleep: Mock) -> None:
    response = make_response()
    response.json.side_effect = ValueError("no json")
    mock_get.return_value = response

    with pytest.raises(InvalidResponseError, match="не JSON"):
        get_json(URL)
