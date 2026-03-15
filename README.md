# Описание проекта

Сервис сокращения ссылок на `FastAPI + PostgreSQL + Redis`.

## Единая версия Python и единый venv

Проект приведён к одной версии Python: `3.12`.

- Docker использует `python:3.12-slim`.
- Локально нужно использовать один виртуальный env: `.venv`.
- Если рядом есть старые окружения вроде `.venv312`, они больше не нужны для работы проекта.

Создание и наполнение единственного окружения:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

## Инструкция по запуску


```bash
. .venv/bin/activate
docker compose up -d --build
```

Веб-интерфейс: `http://localhost:8000/`.

## Описание API

### Auth
- `POST /auth/register` — регистрация пользователя.
- `POST /auth/login` — логин и получение JWT токена.

### Ссылки
- `POST /shorten` — быстрое сокращение длинной ссылки.
- `POST /links/shorten` — расширенное создание (поддержка `custom_alias`, `expires_at`).
- `GET /{short_code}` — редирект на оригинальный URL.
- `GET /links/{short_code}` — редирект на оригинальный URL.
- `GET /links/{short_code}/stats` — статистика по ссылке.
- `GET /links/search?original_url={url}` — поиск по оригинальному URL.
- `GET /links/{short_code}/info` — информация о ссылке.
- `PUT /links/{short_code}` — обновление оригинального URL (только владелец).
- `DELETE /links/{short_code}` — удаление ссылки (только владелец).

### Служебный endpoint
- `GET /health` — проверка состояния сервиса.

## Примеры запросов

### 1. Регистрация

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"123"}'
```

### 2. Логин

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"123"}'
```

### 3. Быстрое сокращение ссылки

```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"original_url":"https://example.com/some/very/long/url"}'
```

Пример ответа:

```json
{
  "original_url": "https://example.com/some/very/long/url",
  "short_url": "http://localhost:8000/Ab12CdE",
  "short_code": "Ab12CdE"
}
```

### 4. Переход по короткой ссылке

```bash
curl -i http://localhost:8000/Ab12CdE
```

### 5. Создание ссылки с alias и expires_at (для авторизованного пользователя)

```bash
TOKEN="<jwt_token>"
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "original_url":"https://example.com/some/very/long/url",
    "custom_alias":"myalias",
    "expires_at":"2026-12-31T23:59:00+03:00"
  }'
```

### 6. Статистика

```bash
curl http://localhost:8000/links/myalias/stats
```

### 7. Поиск по оригинальному URL

```bash
curl "http://localhost:8000/links/search?original_url=https://example.com/some/very/long/url"
```

### 8. Обновление ссылки

```bash
TOKEN="<jwt_token>"
curl -X PUT http://localhost:8000/links/myalias \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"original_url":"https://example.org/new-url"}'
```

### 9. Удаление ссылки

```bash
TOKEN="<jwt_token>"
curl -X DELETE http://localhost:8000/links/myalias \
  -H "Authorization: Bearer $TOKEN"
```

## Описание БД

Основная БД — PostgreSQL.

### Таблица `users`
- `id` — PK.
- `email` — уникальный email пользователя.
- `password_hash` — хэш пароля.
- `created_at` — дата создания пользователя.

### Таблица `links`
- `id` — PK.
- `short_code` — уникальный короткий код.
- `original_url` — оригинальная длинная ссылка.
- `created_at` — дата создания.
- `expires_at` — срок действия ссылки (опционально).
- `click_count` — число переходов.
- `last_accessed_at` — дата последнего перехода.
- `owner_id` — FK на `users.id` (может быть `NULL` для незарегистрированных пользователей).

## Кэширование

Используется Redis:
- `redirect:{short_code}` — кэш оригинального URL для редиректа.
- `stats:{short_code}` — кэш статистики.

При `PUT`/`DELETE` кэш ссылки инвалидируется.

## Фоновые задачи

Раз в минуту выполняется очистка:
- истекших ссылок (`expires_at`),
- неиспользуемых ссылок по `UNUSED_LINK_TTL_DAYS`.

## Тестирование и покрытие

```bash
. .venv/bin/activate
python -m pytest tests
python -m coverage run --source=app -m pytest tests
python -m coverage report -m
python -m coverage html
```

Актуальное покрытие кода приложения (`app/`) составляет `93%`.

- Текстовая инструкция: [tests/TESTING.md](tests/TESTING.md)
