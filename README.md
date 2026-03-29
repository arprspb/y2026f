# Решение: распознавание голосовых команд (олимпиада)

Стек: **FastAPI** (API) + **Vue 3 + Vite** (UI) + **PostgreSQL** + **VOSK**.

## Быстрый запуск (рекомендуется для проверки)

1. Скачайте [vosk-model-small-ru-0.22](https://alphacephei.com/vosk/models) и распакуйте в `./models/vosk-model-small-ru-0.22/`.

2. Скопируйте переменные окружения и при необходимости поправьте секреты:

   ```bash
   cp .env.example .env
   ```

3. Поднимите все сервисы:

   ```bash
   docker compose up --build
   ```

4. Откройте **http://localhost:8080** — интерфейс. Первый зарегистрированный пользователь становится администратором.

Дополнительно: Swagger API — **http://localhost:8000/docs**.

## Локальная разработка

Бэкенд и миграции — как обычно из каталога `backend` (venv, `pip install -e ".[dev]"`, `alembic upgrade head`, `uvicorn`). Нужны **ffmpeg** и файл `.env` (см. [.env.example](.env.example)).

Фронтенд:

```bash
cd frontend
npm ci
npm run dev
```

Dev-сервер: **http://localhost:5173**, запросы к API проксируются на `http://127.0.0.1:8000`. Убедитесь, что в `.env` бэкенда в `CORS_ORIGINS` указаны origin’ы для 5173 и при необходимости 8080.

## Переменные

См. [.env.example](.env.example).

## Тесты бэкенда

```bash
cd backend && source .venv/bin/activate && pytest tests/ -v
```
