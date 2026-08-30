from __future__ import annotations

import json
from functools import lru_cache
from typing import List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_ENV: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Multilingual AI Farmer Advisory Assistant"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]

    # Database: MongoDB & SQL
    DATABASE_TYPE: str = "mongodb"  # mongodb | sqlite | postgresql
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "farmer_ai"
    DATABASE_URL: str = "sqlite+aiosqlite:///./farmer_ai.db"

    JWT_SECRET_KEY: str = "change_this_secret_key_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1024

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    VECTOR_STORE: str = "faiss"
    VECTOR_STORE_PATH: str = "data/vector_store"

    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.70
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    TRANSLATION_PROVIDER: str = "google"
    TRANSLATION_API_KEY: Optional[str] = None

    STT_PROVIDER: str = "openai"
    STT_API_KEY: Optional[str] = None

    TTS_PROVIDER: str = "google"
    TTS_API_KEY: Optional[str] = None

    DISEASE_MODEL_PATH: Optional[str] = None
    DISEASE_CONFIDENCE_THRESHOLD: float = 0.70

    MAX_IMAGE_SIZE_MB: int = 10
    MAX_AUDIO_SIZE_MB: int = 25
    UPLOAD_DIR: str = "uploads"

    MOCK_MODE: bool = True
    ALLOW_ANONYMOUS_QUERY: bool = True

    WEATHER_PROVIDER: Optional[str] = None
    WEATHER_API_KEY: Optional[str] = None

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            v_clean = v.strip()
            if v_clean.startswith("[") and v_clean.endswith("]"):
                try:
                    return json.loads(v_clean)
                except Exception:
                    pass
            return [o.strip() for o in v_clean.split(",") if o.strip()]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
