from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/voice_commands"
    secret_key: str = "change-me-in-production-use-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    upload_dir: str = "./uploads"
    vosk_model_path: str = "./models/vosk-model-small-ru-0.22"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


def get_settings() -> Settings:
    return Settings()
