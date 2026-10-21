"""Application errors into which clients translate failures of external services.

The hierarchy mirrors the CLI exit codes:
- NotFoundError -> 3 (city or currency not found);
- ExternalServiceError -> 4 (service unavailable or answered unexpectedly).
"""


class AppError(Exception):
    """Base class for all application errors."""


class NotFoundError(AppError):
    """An external service does not know the requested entity."""


class CityNotFoundError(NotFoundError):
    def __init__(self, city: str) -> None:
        super().__init__(f"город не найден: {city!r}")
        self.city = city


class CurrencyNotFoundError(NotFoundError):
    def __init__(self, currency: str) -> None:
        super().__init__(f"код валюты не найден: {currency!r}")
        self.currency = currency


class ExternalServiceError(AppError):
    """An external service did not give a usable answer."""


class ServiceUnavailableError(ExternalServiceError):
    """Network error, timeout, 5xx or 429 persisted after all retries."""


class InvalidResponseError(ExternalServiceError):
    """The response failed the format or required-field checks."""


class UpstreamHTTPError(ExternalServiceError):
    """A non-retryable HTTP error status (4xx except 429).

    A concrete client decides whether the status means "not found".
    """

    def __init__(self, url: str, status_code: int, body: str) -> None:
        super().__init__(f"{url} ответил HTTP {status_code}")
        self.url = url
        self.status_code = status_code
        self.body = body[:500]
