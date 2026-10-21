"""Tests of the CLI: the summary builder is mocked, exit codes are checked."""

import json
from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest

from clients.exceptions import CityNotFoundError, ServiceUnavailableError
from main import main
from processing.service import CitySummary

SUMMARY: CitySummary = {
    "city": "Moscow",
    "weather": {"temp_c": 7.6, "description": "partly cloudy", "warm_clothes": False},
    "rates": {"currency": "EUR", "rate_to_rub": 92.85, "expensive": False},
}


@pytest.fixture
def mock_build() -> Iterator[Mock]:
    with patch("main.build_city_summary", return_value=SUMMARY) as mock:
        yield mock


@pytest.fixture(autouse=True)
def fixed_run_id() -> Iterator[None]:
    """Make run_id predictable; the real logging setup stays in place."""
    fake_uuid = Mock()
    fake_uuid.hex = "abc12345deadbeef"
    with patch("logging_config.uuid.uuid4", return_value=fake_uuid):
        yield


def test_text_output(mock_build: Mock, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--city", "Moscow", "--currency", "EUR"])

    assert code == 0
    assert capsys.readouterr().out == (
        "Город: Moscow\n"
        "Погода: 7.6°C, partly cloudy\n"
        "Тёплая одежда: нет\n"
        "EUR→RUB: 92.85\n"
        "Дорогой курс: нет\n"
    )


def test_json_output(mock_build: Mock, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--city", "Moscow", "--currency", "EUR", "--json"])

    assert code == 0
    assert json.loads(capsys.readouterr().out) == SUMMARY


def test_city_not_found_gives_exit_code_3(
    mock_build: Mock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_build.side_effect = CityNotFoundError("Qwzxzzxq")

    code = main(["--city", "Qwzxzzxq"])

    captured = capsys.readouterr()
    assert code == 3
    assert captured.out == ""
    assert "Qwzxzzxq" in captured.err
    assert "run_id=abc12345" in captured.err


def test_service_error_gives_exit_code_4(
    mock_build: Mock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_build.side_effect = ServiceUnavailableError("down")

    code = main(["--city", "Moscow"])

    assert code == 4
    assert "run_id=abc12345" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--city", "   "],
        ["--city", "Moscow", "--currency", "12"],
        ["--city", "Moscow", "--currency", "EURO"],
    ],
)
def test_bad_arguments_give_exit_code_2(mock_build: Mock, argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(argv)

    assert exc_info.value.code == 2
    mock_build.assert_not_called()


def test_currency_is_upper_cased(mock_build: Mock) -> None:
    main(["--city", "Moscow", "--currency", "eur"])

    mock_build.assert_called_once_with("Moscow", "EUR", use_cache=True)


def test_defaults_and_stripped_city(mock_build: Mock) -> None:
    main(["--city", "  Moscow "])

    mock_build.assert_called_once_with("Moscow", "USD", use_cache=True)


def test_no_cache_flag(mock_build: Mock) -> None:
    main(["--city", "Moscow", "--no-cache"])

    mock_build.assert_called_once_with("Moscow", "USD", use_cache=False)
