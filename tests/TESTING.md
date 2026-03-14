# Тестирование сервиса сокращения ссылок

## Что покрыто

- Юнит-тесты для генерации short code, кэша, JWT/хэширования, настроек, зависимостей auth, cleanup-задачи.
- Юнит-тесты для `AuthService` и `LinkService`, включая ошибки, коллизии short code, кэшированные редиректы и проверку прав.
- Функциональные API-тесты через `httpx.AsyncClient` для `auth`, публичного сокращения, редиректов, поиска, статистики и полного CRUD цикла.
- Нагрузочный сценарий Locust в [tests/locustfile.py](/Users/glebfadeev/Downloads/Python%20HW3/python_hw3/tests/locustfile.py).

## Как запускать

Целевая версия Python: `3.12`.

Используется один виртуальный env: `.venv`.

Создать и подготовить окружение:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Запустить тесты:

```bash
. .venv/bin/activate
python -m pytest tests
```

Проверить покрытие:

```bash
. .venv/bin/activate
python -m coverage run --source=app -m pytest tests
python -m coverage report -m
python -m coverage html
```

Последний проверенный результат покрытия для `app/`: `93%`.

HTML-отчёт открывается из файла [htmlcov/index.html](/Users/glebfadeev/Downloads/Python HW3/python_hw3/htmlcov/index.html).

## Нагрузочное тестирование

Поднять сервис и выполнить Locust:

```bash
locust -f tests/locustfile.py --host http://localhost:8000
```

Рекомендуемый базовый сценарий:

- `20` пользователей, `spawn rate 5` для smoke-проверки.
- `100` пользователей, `spawn rate 10` для оценки деградации на массовом создании ссылок.
- Сравнить ответы `GET /{short_code}` и `GET /links/{short_code}/stats` в серии повторных запросов, чтобы оценить эффект Redis-кэша.
