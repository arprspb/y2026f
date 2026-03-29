# Решение: распознавание голосовых команд (олимпиада)

Стек: **FastAPI** (API) + **Vue 3 + Vite** (UI) + **PostgreSQL** + **VOSK**.

## Быстрый запуск (рекомендуется для проверки)

1. **Модель VOSK (русская, для сервера)** по умолчанию — **[vosk-model-ru-0.42](https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip)** (~1.8 ГБ, качество заметно выше, чем у small). Лицензия Apache 2.0. Скачайте архив и распакуйте так, чтобы по пути `models/vosk-model-ru-0.42/` лежал файл `am/final.mdl` (при необходимости перенесите содержимое из вложенной папки внутри архива на уровень выше).

   ```bash
   mkdir -p models && cd models
   wget https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip
   unzip vosk-model-ru-0.42.zip
   # Должно получиться: models/vosk-model-ru-0.42/am/final.mdl
   ```

   Крупные модели VOSK рассчитаны на машины с достаточным объёмом RAM (ориентир — единицы–десятки ГБ под загрузку модели; точное число зависит от ОС и версии). Для слабых ПК можно указать в `.env` путь на облегчённую **[vosk-model-small-ru-0.22](https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip)** (~45 МБ) в `VOSK_MODEL_PATH`.

2. Скопируйте переменные окружения и при необходимости поправьте секреты:

   ```bash
   cp .env.example .env
   ```

3. Поднимите все сервисы:

   ```bash
   docker compose up --build
   ```

4. Откройте **http://localhost:8080** — интерфейс. Войдите под учётной записью из `BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD` (в Docker Compose по умолчанию `admin` / `admin`; смените в продакшене). Новых пользователей создаёт только администратор на странице «Пользователи»; публичная регистрация отключена.

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
