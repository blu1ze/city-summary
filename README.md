# City Summary — «Сводка по городу»

CLI-утилита: получает текущую погоду в городе и курс выбранной валюты к рублю из внешних API,
проверяет ответы, применяет правила предобработки и печатает сводку.

```text
$ python main.py --city Moscow --currency EUR
Город: Moscow
Погода: 7.6°C, partly cloudy
Тёплая одежда: нет
EUR→RUB: 92.85
Дорогой курс: нет
```

## Требования

- Python 3.12
- Доступ в интернет (ключи API не нужны)

## Установка

Вариант 1 — `venv` + `pip`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Вариант 2 — [uv](https://docs.astral.sh/uv/) (сам поставит Python 3.12 и зависимости из `uv.lock`):

```bash
uv sync
source .venv/bin/activate
```

## Запуск

```bash
python main.py --city Moscow                  # курс USD→RUB (по умолчанию)
python main.py --city Moscow --currency EUR   # курс EUR→RUB
python main.py --city "Saint Petersburg" --json
python main.py --city Moscow -v               # подробные логи в stderr
```

| Аргумент | Описание |
|---|---|
| `--city` | Город (обязательный). Регистр не важен: `moscow` → `Moscow`. |
| `--currency` | Код валюты из трёх латинских букв, по умолчанию `USD`. |
| `--json` | Вывести сводку в JSON вместо текста. |
| `--no-cache` | Не использовать кэш курса. |
| `-v`, `--verbose` | Логи уровня DEBUG в stderr (по умолчанию — только предупреждения). |

### Коды выхода

| Код | Когда |
|---|---|
| `0` | Успех |
| `2` | Ошибка аргументов (нет `--city`, пустой город, `--currency 12`, ...) |
| `3` | Город или код валюты не найден (`--city Qwzxzzxq`, `--currency XYZ`) |
| `4` | Внешний сервис недоступен после повторов или вернул некорректный ответ |

Сообщение об ошибке пишется в stderr вместе с `run_id` для поиска по логам.

### JSON-вывод

```json
{
  "city": "Moscow",
  "weather": {"temp_c": 7.6, "description": "partly cloudy", "warm_clothes": false},
  "rates": {"currency": "EUR", "rate_to_rub": 92.85, "expensive": false}
}
```

## Внешние API

| Данные | API | Запросы |
|---|---|---|
| Погода | [Open-Meteo](https://open-meteo.com/en/docs) | `GET geocoding-api.open-meteo.com/v1/search` → координаты, затем `GET api.open-meteo.com/v1/forecast?current=temperature_2m,weather_code` |
| Курс | [Frankfurter](https://frankfurter.dev) | `GET api.frankfurter.dev/v2/rate/{currency}/RUB` |

Open-Meteo отдаёт погоду кодом WMO — клиент переводит его в текст (`0` → `clear sky`).

## Архитектура

```text
city-summary/
├── main.py             # CLI: argparse, вызов build_city_summary, вывод, коды выхода
├── logging_config.py   # structlog -> stderr, run_id в каждой записи
├── clients/            # только общение с внешними API
│   ├── http.py         # общий GET: timeout, retry, Retry-After, разбор JSON
│   ├── validation.py   # Pydantic-схемы ответов -> InvalidResponseError
│   ├── exceptions.py   # исключения приложения (NotFound -> 3, ExternalService -> 4)
│   ├── cache.py        # файловый TTL-кэш
│   ├── weather.py      # get_weather(city) -> WeatherData
│   └── rates.py        # get_rate(currency) -> float, кэш на 5 минут
├── processing/
│   ├── preprocessing.py  # правила: warm_clothes, expensive, описание по умолчанию, округление
│   └── service.py        # build_city_summary(city, currency="USD") -> CitySummary
├── tests/              # pytest + unittest.mock, сеть не трогают
└── .github/workflows/ci.yml  # GitHub Actions: ruff, mypy, pytest
```

- `clients/` не печатает в консоль и не знает про CLI — только HTTP, проверка ответов
  и перевод ошибок внешних сервисов в исключения приложения.
- `processing/` не делает HTTP-запросов сам — получает данные от клиентов и применяет правила.
- `main.py` переводит исключения в коды выхода и печатает результат.

## Надёжность HTTP

- Только `GET`, timeout **5 с** на каждый запрос.
- **2 повтора** после первой попытки (всего 3) при `Timeout`, `ConnectionError`
  и HTTP 500/502/503/504; пауза 0.5 с, затем 1 с.
- HTTP 429: ждём столько, сколько сказано в числовом `Retry-After`. Если он больше 10 с —
  сразу код 4, а не зависание. Если заголовка нет или он в формате даты — обычная пауза.
- Прочие 4xx не повторяются. Frankfurter на неизвестный код валюты отвечает 404/422 → код выхода 3.
- Ответ проверяется Pydantic-схемой в strict-режиме: обязательные поля и их типы
  (`"rate": "83.9"` строкой — ошибка), диапазоны (курс > 0, широта ±90), отсутствие NaN/inf,
  совпадение валютной пары. Любое несоответствие → `InvalidResponseError` с названием поля.

## Правила предобработки

Все правила — в `processing/preprocessing.py`:

| Правило | Условие |
|---|---|
| `warm_clothes` | температура < 0 °C |
| `expensive` | курс > 100 ₽ |
| Описание погоды по умолчанию | пустое описание (неизвестный код WMO) → `нет данных` |
| Точность курса | курс ≥ 1 — до копеек, меньше 1 — 4 значащие цифры (0.1862, а не 0.19) |

Флаги считаются по округлённым значениям, чтобы вывод был согласован: `-0.04 °C` выводится как
`0.0°C`, и тёплая одежда при этом не нужна.

## Дополнительно

- **Логи с `run_id`** — structlog; каждая запись запуска помечена коротким `run_id`; логи идут в
  stderr, stdout остаётся чистым для сводки и `--json`. Повторные попытки HTTP видны как
  предупреждения, подробности — с флагом `-v`.
- **Кэш курса на 5 минут** — файл `~/.cache/city_summary/rates.json` (переопределяется через
  `CITY_SUMMARY_CACHE_DIR` или `XDG_CACHE_HOME`). Кэш в памяти бесполезен — процесс CLI живёт доли
  секунды. Ошибки чтения или записи кэша не ломают запрос. Отключается флагом `--no-cache`.
- **Тесты клиентов через `unittest.mock`** — повторы, `Retry-After`, проверка ответов, коды выхода, кэш.
- **Типизация** — `mypy --strict`, Pydantic для внешних данных, TypedDict для сводки.
- **Флаг `--json`**.
- **CI** — GitHub Actions: ruff, mypy, pytest, синхронность `requirements*.txt` с `uv.lock`.

## Разработка

```bash
uv sync                      # или: pip install -r requirements-dev.txt
uv run pytest                # или: pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

Зависимости описаны в `pyproject.toml` и зафиксированы в `uv.lock`; `requirements*.txt`
генерируются из lock-файла:

```bash
uv export --format requirements-txt --no-hashes --no-dev --no-emit-project -o requirements.txt
uv export --format requirements-txt --no-hashes --no-emit-project -o requirements-dev.txt
```
