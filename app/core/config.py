from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_DATABASE_URL = "postgresql+psycopg://medwork:medwork@localhost:5432/medwork"


def normalize_database_url(value: str) -> str:
    prepared = value.strip()

    if prepared.startswith("postgres://"):
        return f"postgresql+psycopg://{prepared[len('postgres://'):]}"
    if prepared.startswith("postgresql://"):
        return f"postgresql+psycopg://{prepared[len('postgresql://'):]}"

    return prepared


def build_database_url_from_parts() -> str | None:
    host = os.getenv("PGHOST")
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")
    database = os.getenv("PGDATABASE")

    if not host or not user or password is None or not database:
        return None

    port = os.getenv("PGPORT", "5432")
    query = os.getenv("PGQUERY")
    auth = f"{quote(user)}:{quote(password)}"
    url = f"postgresql+psycopg://{auth}@{host}:{port}/{quote(database)}"
    return f"{url}?{query}" if query else url


def resolve_database_url() -> str | None:
    for candidate in (
        os.getenv("DATABASE_URL"),
        os.getenv("DATABASE_PRIVATE_URL"),
        os.getenv("DATABASE_PUBLIC_URL"),
        build_database_url_from_parts(),
    ):
        if candidate:
            return normalize_database_url(candidate)

    return None


def is_local_database_url(value: str) -> bool:
    lowered = value.lower()
    return "@localhost:" in lowered or "@127.0.0.1:" in lowered or "@[::1]:" in lowered


class Settings(BaseSettings):
    app_name: str = "MedWork Clinic API"
    app_env: str = "development"
    database_url: str | None = None
    cors_origins: list[str] = ["http://localhost:3000"]
    clinic_name: str | None = None
    auth_secret_key: str | None = None
    auth_token_expiration_hours: int = 12

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        enable_decoding=False,
    )

    @model_validator(mode="after")
    def finalize(self) -> "Settings":
        self.database_url = resolve_database_url()

        if not self.database_url:
            if self.app_env == "development":
                self.database_url = DEFAULT_LOCAL_DATABASE_URL
            else:
                raise ValueError(
                    "DATABASE_URL nao configurada. Defina DATABASE_URL, DATABASE_PRIVATE_URL ou as variaveis PG* no ambiente."
                )

        if self.app_env != "development" and is_local_database_url(self.database_url):
            raise ValueError(
                "DATABASE_URL aponta para localhost em producao. No Railway, use a URL do Postgres do proprio projeto."
            )

        self.clinic_name = (self.clinic_name or self.app_name).replace(" API", "").strip() or "Nuemo"
        self.auth_secret_key = (self.auth_secret_key or "").strip()

        if not self.auth_secret_key:
            raise ValueError("AUTH_SECRET_KEY deve ser configurada no ambiente.")
        self.auth_token_expiration_hours = max(1, int(self.auth_token_expiration_hours))

        return self

    @field_validator("cors_origins", mode="before")
    @classmethod
    def normalize_cors_origins(cls, value: str | list[str]) -> list[str]:
        return cls.parse_cors_origins(value)

    @staticmethod
    def parse_cors_origins(value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                loaded = json.loads(stripped)
                if isinstance(loaded, list):
                    return [str(origin).strip() for origin in loaded if str(origin).strip()]
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return ["http://localhost:3000"]


settings = Settings()

