from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TipoEmpresa


def normalize_document(value: str | None) -> str | None:
    if value is None:
        return None

    digits = re.sub(r"\D", "", value)
    if not digits:
        return None
    if len(digits) not in {11, 14}:
        raise ValueError("Informe um CPF ou CNPJ valido.")
    return digits


class CompanyBase(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    tipo: TipoEmpresa
    documento: str | None = Field(default=None, max_length=18)
    contato: str | None = Field(default=None, max_length=255)

    @field_validator("nome")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("documento")
    @classmethod
    def validate_document(cls, value: str | None) -> str | None:
        return normalize_document(value)

    @field_validator("contato")
    @classmethod
    def validate_contact(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(CompanyBase):
    pass


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    tipo: TipoEmpresa
    documento: str | None = None
    contato: str | None = None
