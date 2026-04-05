from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def normalize_auth_username(value: str) -> str:
    return value.strip().lower()


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return normalize_auth_username(value)


class AuthRegisterRequest(BaseModel):
    nome: str | None = Field(default=None, max_length=255)
    username: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=255)

    @field_validator("nome")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return normalize_auth_username(value)


class AuthUserRead(BaseModel):
    id: int
    nome: str | None = None
    username: str
    created_at: datetime


class AuthLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: AuthUserRead
