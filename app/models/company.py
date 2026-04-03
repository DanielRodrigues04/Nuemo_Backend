from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TipoEmpresa

if TYPE_CHECKING:
    from app.models.attendance import Atendimento


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    tipo: Mapped[TipoEmpresa] = mapped_column(SqlEnum(TipoEmpresa, native_enum=False), nullable=False)
    documento: Mapped[str | None] = mapped_column(String(18), unique=True, nullable=True)
    contato: Mapped[str | None] = mapped_column(String(255), nullable=True)

    atendimentos: Mapped[list["Atendimento"]] = relationship(back_populates="empresa")
