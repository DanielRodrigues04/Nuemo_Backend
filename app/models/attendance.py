from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import FormaPagamento, StatusAtendimento


class Atendimento(Base):
    __tablename__ = "atendimentos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    competencia_cobranca: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    data_pagamento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    nome_paciente: Mapped[str] = mapped_column(String(255), nullable=False)
    cpf_paciente: Mapped[str | None] = mapped_column(String(14), nullable=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False)
    exame_id: Mapped[int] = mapped_column(ForeignKey("exames.id", ondelete="RESTRICT"), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    forma_pagamento: Mapped[FormaPagamento] = mapped_column(SqlEnum(FormaPagamento, native_enum=False), nullable=False)
    status: Mapped[StatusAtendimento] = mapped_column(SqlEnum(StatusAtendimento, native_enum=False), nullable=False)

    empresa = relationship("Empresa", back_populates="atendimentos")
    exame = relationship("Exame", back_populates="atendimentos")
