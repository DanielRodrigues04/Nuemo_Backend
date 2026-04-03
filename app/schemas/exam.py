from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExamCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    valor: float = Field(gt=0)


class ExamUpdate(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    valor: float = Field(gt=0)


class ExamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    valor: float
