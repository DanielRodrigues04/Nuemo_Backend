from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import FormaPagamento, StatusAtendimento


def normalize_patient_cpf(value: str | None) -> str | None:
    if value is None:
        return None

    digits = re.sub(r"\D", "", value)
    if not digits:
        return None
    if len(digits) != 11:
        raise ValueError("Informe um CPF valido para o paciente.")
    return digits


class AttendanceBase(BaseModel):
    nome_paciente: str = Field(min_length=2, max_length=255)
    cpf_paciente: str | None = Field(default=None, max_length=14)
    empresa_id: int = Field(gt=0)
    exame_id: int = Field(gt=0)
    valor: float | None = Field(default=None, ge=0)
    forma_pagamento: FormaPagamento

    @field_validator("nome_paciente")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("cpf_paciente")
    @classmethod
    def validate_patient_cpf(cls, value: str | None) -> str | None:
        return normalize_patient_cpf(value)


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(AttendanceBase):
    pass


class AttendancePay(BaseModel):
    forma_pagamento: FormaPagamento | None = None


class AttendanceRead(BaseModel):
    id: int
    data: datetime
    competencia_cobranca: date
    data_pagamento: datetime | None = None
    nome_paciente: str
    cpf_paciente: str | None = None
    empresa_id: int
    empresa_nome: str
    exame_id: int
    exame_nome: str
    valor: float
    forma_pagamento: FormaPagamento
    status: StatusAtendimento
