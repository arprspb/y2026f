from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/voice_commands"
    secret_key: str = "change-me-in-production-use-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    upload_dir: str = "./uploads"
    # Крупная русская модель по умолчанию (качество лучше, чем у small-ru). См. README — скачать архив.
    vosk_model_path: str = "./models/vosk-model-ru-0.42"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Первичный администратор: создаётся при старте, если пользователя с таким логином ещё нет.
    # Роль admin через API создавать нельзя — только эти переменные или правка БД.
    bootstrap_admin_username: str = ""
    bootstrap_admin_password: str = ""


def get_settings() -> Settings:
    return Settings()
