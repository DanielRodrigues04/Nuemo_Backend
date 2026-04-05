from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import FormaPagamento, StatusAtendimento
from app.schemas.report import (
    CompanyDetailReport,
    CompanySettlementReport,
    CompanySettlementRequest,
    DashboardReport,
    DebtorCompanyReport,
    ExamGroupReport,
    MonthListReport,
    MonthlyCloseReport,
)
from app.services.attendance_service import list_attendance_models, resolve_period_filters
from app.services.company_service import get_company
from app.services.pdf_service import generate_company_statement_pdf
from app.services.serializers import decimal_to_float, serialize_attendance, serialize_company


def month_key(value: date | datetime) -> str:
    return f"{value.year}-{value.month:02d}"


def format_currency(value: float) -> str:
    raw = f"{value:,.2f}"
    return f"R$ {raw.replace(',', 'X').replace('.', ',').replace('X', '.')}"


def sum_attendance_values(attendances: list) -> float:
    return round(sum(decimal_to_float(attendance.valor) for attendance in attendances), 2)


def get_reference_month(attendances: list) -> str:
    current_month = month_key(datetime.now(timezone.utc))
    months = sorted({month_key(item.competencia_cobranca) for item in attendances}, reverse=True)

    if current_month in months:
        return current_month
    if months:
        return months[0]
    return current_month


def build_company_detail_report(
    company,
    attendances: list,
    *,
    month: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> CompanyDetailReport:
    if not attendances:
        return CompanyDetailReport(
            empresa=serialize_company(company),
            mes_referencia=month,
            periodo_inicio=period_start,
            periodo_fim=period_end,
            total_exames=0,
            valor_total=0,
            valor_recebido=0,
            valor_pendente=0,
            exames_por_tipo=[],
            atendimentos=[],
        )

    grouped_exams: dict[int, dict[str, float | int | str]] = defaultdict(
        lambda: {
            "exame_id": 0,
            "exame_nome": "",
            "quantidade": 0,
            "valor_total": 0.0,
        }
    )

    for attendance in attendances:
        current = grouped_exams[attendance.exame_id]
        current["exame_id"] = attendance.exame_id
        current["exame_nome"] = attendance.exame.nome
        current["quantidade"] += 1
        current["valor_total"] = round(float(current["valor_total"]) + decimal_to_float(attendance.valor), 2)

    exam_groups = [
        ExamGroupReport(
            exame_id=int(item["exame_id"]),
            exame_nome=str(item["exame_nome"]),
            quantidade=int(item["quantidade"]),
            valor_total=float(item["valor_total"]),
        )
        for item in sorted(grouped_exams.values(), key=lambda current: float(current["valor_total"]), reverse=True)
    ]

    received = [item for item in attendances if item.status == StatusAtendimento.PAGO]
    pending = [item for item in attendances if item.status == StatusAtendimento.PENDENTE]

    return CompanyDetailReport(
        empresa=serialize_company(company),
        mes_referencia=month,
        periodo_inicio=period_start,
        periodo_fim=period_end,
        total_exames=len(attendances),
        valor_total=sum_attendance_values(attendances),
        valor_recebido=sum_attendance_values(received),
        valor_pendente=sum_attendance_values(pending),
        exames_por_tipo=exam_groups,
        atendimentos=[serialize_attendance(attendance) for attendance in attendances],
    )


def get_dashboard_report(db: Session) -> DashboardReport:
    all_attendances = list_attendance_models(db)
    reference_month = get_reference_month(all_attendances)
    attendances = [item for item in all_attendances if month_key(item.competencia_cobranca) == reference_month]

    received = [item for item in attendances if item.status == StatusAtendimento.PAGO]
    pending = [item for item in attendances if item.status == StatusAtendimento.PENDENTE]
    companies_with_pending = {item.empresa_id for item in pending}

    return DashboardReport(
        mes_referencia=reference_month,
        total_faturado=sum_attendance_values(attendances),
        total_recebido=sum_attendance_values(received),
        total_pendente=sum_attendance_values(pending),
        quantidade_pendencias=len(pending),
        empresas_com_pendencia=len(companies_with_pending),
    )


def get_months_report(db: Session) -> MonthListReport:
    months = sorted({month_key(item.competencia_cobranca) for item in list_attendance_models(db)}, reverse=True)
    return MonthListReport(meses=months)


def get_month_report(db: Session, month: str) -> MonthlyCloseReport:
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mes invalido. Use o formato YYYY-MM.",
        ) from exc

    attendances = list_attendance_models(db, month=month, use_billing_competence=True)
    pending_by_company: dict[int, dict[str, float | int | str | None]] = defaultdict(
        lambda: {
            "empresa_id": 0,
            "empresa_nome": "",
            "documento": None,
            "contato": None,
            "total_pendente": 0.0,
            "quantidade_atendimentos": 0,
        }
    )

    for attendance in attendances:
        if attendance.status != StatusAtendimento.PENDENTE:
            continue

        current = pending_by_company[attendance.empresa_id]
        current["empresa_id"] = attendance.empresa_id
        current["empresa_nome"] = attendance.empresa.nome
        current["documento"] = attendance.empresa.documento
        current["contato"] = attendance.empresa.contato
        current["total_pendente"] = round(float(current["total_pendente"]) + decimal_to_float(attendance.valor), 2)
        current["quantidade_atendimentos"] += 1

    received = [item for item in attendances if item.status == StatusAtendimento.PAGO]
    pending = [item for item in attendances if item.status == StatusAtendimento.PENDENTE]
    debtors = [
        DebtorCompanyReport(
            empresa_id=int(item["empresa_id"]),
            empresa_nome=str(item["empresa_nome"]),
            documento=item["documento"] if item["documento"] else None,
            contato=item["contato"] if item["contato"] else None,
            total_pendente=float(item["total_pendente"]),
            quantidade_atendimentos=int(item["quantidade_atendimentos"]),
        )
        for item in sorted(pending_by_company.values(), key=lambda current: float(current["total_pendente"]), reverse=True)
    ]

    return MonthlyCloseReport(
        mes=month,
        total_faturado=sum_attendance_values(attendances),
        total_recebido=sum_attendance_values(received),
        total_pendente=sum_attendance_values(pending),
        quantidade_pendencias=len(pending),
        empresas_devedoras=debtors,
    )


def get_company_report(
    db: Session,
    company_id: int,
    *,
    month: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
) -> CompanyDetailReport:
    company = get_company(db, company_id)
    period_start, period_end = resolve_period_filters(month=month, date_start=date_start, date_end=date_end)
    attendances = list_attendance_models(
        db,
        company_id=company_id,
        month=month,
        date_start=date_start,
        date_end=date_end,
        use_billing_competence=True,
    )

    return build_company_detail_report(
        company,
        attendances,
        month=month,
        period_start=period_start,
        period_end=period_end,
    )


def settle_company_period(db: Session, company_id: int, payload: CompanySettlementRequest) -> CompanySettlementReport:
    company = get_company(db, company_id)
    period_start, period_end = resolve_period_filters(
        month=payload.month,
        date_start=payload.data_inicio,
        date_end=payload.data_fim,
    )
    payment_method = payload.forma_pagamento
    attendances = list_attendance_models(
        db,
        company_id=company_id,
        status=StatusAtendimento.PENDENTE,
        month=payload.month,
        date_start=payload.data_inicio,
        date_end=payload.data_fim,
        use_billing_competence=True,
    )

    if not attendances:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum atendimento pendente foi encontrado para a empresa no periodo informado.",
        )

    payment_date = datetime.now(timezone.utc)
    attendance_ids: list[int] = []
    for attendance in attendances:
        attendance.forma_pagamento = payment_method
        attendance.status = StatusAtendimento.PAGO
        attendance.data_pagamento = payment_date
        attendance_ids.append(attendance.id)
        db.add(attendance)

    db.commit()

    return CompanySettlementReport(
        empresa=serialize_company(company),
        mes_referencia=payload.month,
        periodo_inicio=period_start or attendances[-1].data.date().isoformat(),
        periodo_fim=period_end or attendances[0].data.date().isoformat(),
        forma_pagamento=payment_method,
        quantidade_atendimentos=len(attendances),
        total_baixado=sum_attendance_values(attendances),
        atendimentos_ids=attendance_ids,
    )


def generate_company_report_pdf(
    db: Session,
    company_id: int,
    *,
    month: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
) -> bytes:
    report = get_company_report(
        db,
        company_id,
        month=month,
        date_start=date_start,
        date_end=date_end,
    )

    period_label = report.mes_referencia or (
        f"{report.periodo_inicio or '--'} a {report.periodo_fim or '--'}"
        if report.periodo_inicio or report.periodo_fim
        else "Historico completo"
    )
    return generate_company_statement_pdf(
        report,
        clinic_name=settings.clinic_name,
        period_label=period_label,
    )
