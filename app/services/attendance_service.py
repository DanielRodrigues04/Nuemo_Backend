from __future__ import annotations

import calendar
from datetime import date, datetime, time, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import Atendimento
from app.models.enums import FormaPagamento, StatusAtendimento
from app.schemas.attendance import AttendanceCreate, AttendancePay, AttendanceRead, AttendanceUpdate
from app.services.company_service import get_company
from app.services.exam_service import get_exam
from app.services.serializers import serialize_attendance


def resolve_attendance_status(payment_method: FormaPagamento) -> StatusAtendimento:
    if payment_method == FormaPagamento.FATURADO:
        return StatusAtendimento.PENDENTE
    return StatusAtendimento.PAGO


def build_attendance_query() -> Select[tuple[Atendimento]]:
    return select(Atendimento).options(
        joinedload(Atendimento.empresa),
        joinedload(Atendimento.exame),
    )


def parse_date_range(value: str, end_of_day: bool = False) -> datetime:
    parsed = date.fromisoformat(value)
    selected_time = time.max if end_of_day else time.min
    return datetime.combine(parsed, selected_time, tzinfo=timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def month_start(value: date) -> date:
    return value.replace(day=1)


def next_month_start(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def resolve_competencia_cobranca(reference_date: datetime, payment_method: FormaPagamento) -> date:
    billing_month = month_start(ensure_utc(reference_date).date())
    if payment_method == FormaPagamento.FATURADO:
        return next_month_start(billing_month)
    return billing_month


def resolve_payment_date(
    payment_method: FormaPagamento,
    current_payment_date: datetime | None = None,
    *,
    keep_existing: bool = True,
) -> datetime | None:
    if payment_method == FormaPagamento.FATURADO:
        return None
    if keep_existing and current_payment_date is not None:
        return current_payment_date
    return datetime.now(timezone.utc)


def resolve_period_filters(
    *,
    month: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
) -> tuple[str | None, str | None]:
    if month and (date_start or date_end):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use apenas month ou data_inicio/data_fim para definir o periodo.",
        )

    if month:
        try:
            parsed = datetime.strptime(month, "%Y-%m")
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mes invalido. Use o formato YYYY-MM.",
            ) from exc

        last_day = calendar.monthrange(parsed.year, parsed.month)[1]
        return (
            f"{parsed.year}-{parsed.month:02d}-01",
            f"{parsed.year}-{parsed.month:02d}-{last_day:02d}",
        )

    if date_start and date_end:
        try:
            start_value = date.fromisoformat(date_start)
            end_value = date.fromisoformat(date_end)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Periodo invalido. Use o formato YYYY-MM-DD.",
            ) from exc

        if start_value > end_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="data_inicio nao pode ser maior que data_fim.",
            )
        return date_start, date_end

    if date_start or date_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe data_inicio e data_fim juntos.",
        )

    return None, None


def list_attendance_models(
    db: Session,
    *,
    company_id: int | None = None,
    status: StatusAtendimento | None = None,
    month: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    use_billing_competence: bool = False,
) -> list[Atendimento]:
    resolved_start, resolved_end = resolve_period_filters(month=month, date_start=date_start, date_end=date_end)
    query = build_attendance_query()

    if company_id is not None:
        query = query.where(Atendimento.empresa_id == company_id)
    if status is not None:
        query = query.where(Atendimento.status == status)
    if resolved_start:
        if use_billing_competence:
            query = query.where(Atendimento.competencia_cobranca >= date.fromisoformat(resolved_start))
        else:
            query = query.where(Atendimento.data >= parse_date_range(resolved_start))
    if resolved_end:
        if use_billing_competence:
            query = query.where(Atendimento.competencia_cobranca <= date.fromisoformat(resolved_end))
        else:
            query = query.where(Atendimento.data <= parse_date_range(resolved_end, end_of_day=True))

    query = query.order_by(Atendimento.data.desc(), Atendimento.id.desc())
    return db.scalars(query).unique().all()


def list_attendances(
    db: Session,
    *,
    company_id: int | None = None,
    status: StatusAtendimento | None = None,
    month: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
) -> list[AttendanceRead]:
    attendances = list_attendance_models(
        db,
        company_id=company_id,
        status=status,
        month=month,
        date_start=date_start,
        date_end=date_end,
    )
    return [serialize_attendance(attendance) for attendance in attendances]


def get_attendance(db: Session, attendance_id: int) -> Atendimento:
    attendance = db.scalar(build_attendance_query().where(Atendimento.id == attendance_id))
    if attendance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atendimento nao encontrado.")
    return attendance


def get_attendance_read(db: Session, attendance_id: int) -> AttendanceRead:
    return serialize_attendance(get_attendance(db, attendance_id))


def create_attendance(db: Session, payload: AttendanceCreate) -> AttendanceRead:
    company = get_company(db, payload.empresa_id)
    exam = get_exam(db, payload.exame_id)
    payment_method = payload.forma_pagamento
    amount = Decimal(str(payload.valor)) if payload.valor is not None else exam.valor
    attendance_date = datetime.now(timezone.utc)

    attendance = Atendimento(
        data=attendance_date,
        competencia_cobranca=resolve_competencia_cobranca(attendance_date, payment_method),
        data_pagamento=resolve_payment_date(payment_method, keep_existing=False),
        nome_paciente=payload.nome_paciente.strip(),
        cpf_paciente=payload.cpf_paciente,
        empresa_id=company.id,
        exame_id=exam.id,
        valor=amount,
        forma_pagamento=payment_method,
        status=resolve_attendance_status(payment_method),
    )

    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    attendance = get_attendance(db, attendance.id)
    return serialize_attendance(attendance)


def update_attendance(db: Session, attendance_id: int, payload: AttendanceUpdate) -> AttendanceRead:
    attendance = get_attendance(db, attendance_id)
    company = get_company(db, payload.empresa_id)
    exam = get_exam(db, payload.exame_id)
    payment_method = payload.forma_pagamento
    amount = Decimal(str(payload.valor)) if payload.valor is not None else exam.valor

    attendance.nome_paciente = payload.nome_paciente.strip()
    attendance.cpf_paciente = payload.cpf_paciente
    attendance.empresa_id = company.id
    attendance.exame_id = exam.id
    attendance.valor = amount
    attendance.forma_pagamento = payment_method
    attendance.status = resolve_attendance_status(payment_method)
    attendance.competencia_cobranca = resolve_competencia_cobranca(attendance.data, payment_method)
    attendance.data_pagamento = resolve_payment_date(payment_method, attendance.data_pagamento)

    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    attendance = get_attendance(db, attendance.id)
    return serialize_attendance(attendance)


def pay_attendance(db: Session, attendance_id: int, payload: AttendancePay) -> AttendanceRead:
    attendance = get_attendance(db, attendance_id)
    payment_method = payload.forma_pagamento or FormaPagamento.PIX

    if payment_method == FormaPagamento.FATURADO:
        payment_method = FormaPagamento.PIX

    attendance.forma_pagamento = payment_method
    attendance.status = StatusAtendimento.PAGO
    attendance.data_pagamento = datetime.now(timezone.utc)

    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    attendance = get_attendance(db, attendance.id)
    return serialize_attendance(attendance)


def delete_attendance(db: Session, attendance_id: int) -> None:
    attendance = get_attendance(db, attendance_id)
    db.delete(attendance)
    db.commit()
