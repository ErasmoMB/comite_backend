import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    PROJECT_NAME: str = "Comité de Ética API"
    API_V1_STR: str = "/api/v1"
    ALLOWED_HOSTS: list = ["*"]

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(BASE_DIR / 'comite_new_test.db').as_posix()}"
    )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
    )

def get_settings():
    return Settings()

settings = get_settings()