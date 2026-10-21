"""CLI entrypoint: parse arguments, print the summary, return an exit code."""

import argparse
import json
import re
import sys
from collections.abc import Sequence
from typing import Final

import structlog

from clients.exceptions import AppError, ExternalServiceError, NotFoundError
from logging_config import configure_logging
from processing.service import CitySummary, build_city_summary

log = structlog.get_logger(__name__)

EXIT_OK: Final = 0
EXIT_BAD_ARGS: Final = 2  # argparse itself exits with 2 on invalid arguments
EXIT_NOT_FOUND: Final = 3
EXIT_SERVICE_ERROR: Final = 4

CURRENCY_PATTERN: Final = re.compile(r"[A-Za-z]{3}")


def city_name(value: str) -> str:
    """Argument type: a non-empty city name."""
    city = value.strip()
    if not city:
        raise argparse.ArgumentTypeError("город не может быть пустым")
    return city


def currency_code(value: str) -> str:
    """Argument type: an ISO currency code of three Latin letters."""
    if not CURRENCY_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "код валюты — три латинские буквы, например USD"
        )
    return value.upper()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Сводка по городу: погода и курс валюты к рублю.",
    )
    parser.add_argument(
        "--city",
        type=city_name,
        required=True,
        help="название города",
    )
    parser.add_argument(
        "--currency",
        type=currency_code,
        default="USD",
        help="код валюты из трёх латинских букв (по умолчанию USD)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="вывести сводку в формате JSON",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="подробные логи в stderr",
    )
    return parser


def yes_no(value: bool) -> str:
    return "да" if value else "нет"


def format_rate(rate: float) -> str:
    """Show rates >= 1 with kopecks, keep digits of small rates."""
    return f"{rate:.2f}" if rate >= 1 else f"{rate:g}"


def format_text(summary: CitySummary) -> str:
    weather = summary["weather"]
    rates = summary["rates"]
    lines = [
        f"Город: {summary['city']}",
        f"Погода: {weather['temp_c']:.1f}°C, {weather['description']}",
        f"Тёплая одежда: {yes_no(weather['warm_clothes'])}",
        f"{rates['currency']}→RUB: {format_rate(rates['rate_to_rub'])}",
        f"Дорогой курс: {yes_no(rates['expensive'])}",
    ]
    return "\n".join(lines)


def report_error(exc: AppError, run_id: str) -> None:
    """Print the error with the run_id, so the log lines can be found."""
    print(f"Ошибка: {exc} (run_id={run_id})", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    args = build_parser().parse_args(argv)
    run_id = configure_logging(verbose=args.verbose)
    log.debug("run_started", city=args.city, currency=args.currency)

    try:
        summary = build_city_summary(args.city, args.currency)
    except NotFoundError as exc:
        report_error(exc, run_id)
        return EXIT_NOT_FOUND
    except ExternalServiceError as exc:
        report_error(exc, run_id)
        return EXIT_SERVICE_ERROR

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(format_text(summary))
    log.debug("run_finished")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
