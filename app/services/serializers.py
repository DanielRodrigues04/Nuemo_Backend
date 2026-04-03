from __future__ import annotations

from decimal import Decimal

from app.models.attendance import Atendimento
from app.models.company import Empresa
from app.models.exam import Exame
from app.schemas.attendance import AttendanceRead
from app.schemas.company import CompanyRead
from app.schemas.exam import ExamRead


def decimal_to_float(value: Decimal | float | int) -> float:
    return float(value)


def serialize_company(company: Empresa) -> CompanyRead:
    return CompanyRead.model_validate(company)


def serialize_exam(exam: Exame) -> ExamRead:
    return ExamRead(id=exam.id, nome=exam.nome, valor=decimal_to_float(exam.valor))


def serialize_attendance(attendance: Atendimento) -> AttendanceRead:
    return AttendanceRead(
        id=attendance.id,
        data=attendance.data,
        nome_paciente=attendance.nome_paciente,
        cpf_paciente=attendance.cpf_paciente,
        empresa_id=attendance.empresa_id,
        empresa_nome=attendance.empresa.nome,
        exame_id=attendance.exame_id,
        exame_nome=attendance.exame.nome,
        valor=decimal_to_float(attendance.valor),
        forma_pagamento=attendance.forma_pagamento,
        status=attendance.status,
    )
