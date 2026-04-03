from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.report import (
    CompanyDetailReport,
    CompanySettlementReport,
    CompanySettlementRequest,
    DashboardReport,
    MonthListReport,
    MonthlyCloseReport,
)
from app.services.report_service import (
    generate_company_report_pdf,
    get_company_report,
    get_dashboard_report,
    get_month_report,
    get_months_report,
    settle_company_period,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/dashboard", response_model=DashboardReport)
def dashboard_report(db: Session = Depends(get_db)) -> DashboardReport:
    return get_dashboard_report(db)


@router.get("/months", response_model=MonthListReport)
def months_report(db: Session = Depends(get_db)) -> MonthListReport:
    return get_months_report(db)


@router.get("/month/{month}", response_model=MonthlyCloseReport)
def monthly_close_report(month: str, db: Session = Depends(get_db)) -> MonthlyCloseReport:
    return get_month_report(db, month)


@router.get("/company/{company_id}", response_model=CompanyDetailReport)
def company_report(
    company_id: int,
    month: str | None = Query(default=None),
    data_inicio: str | None = Query(default=None),
    data_fim: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> CompanyDetailReport:
    return get_company_report(
        db,
        company_id,
        month=month,
        date_start=data_inicio,
        date_end=data_fim,
    )


@router.post("/company/{company_id}/settle", response_model=CompanySettlementReport)
def company_settlement(
    company_id: int,
    payload: CompanySettlementRequest,
    db: Session = Depends(get_db),
) -> CompanySettlementReport:
    return settle_company_period(db, company_id, payload)


@router.get("/company/{company_id}/pdf")
def company_report_pdf(
    company_id: int,
    month: str | None = Query(default=None),
    data_inicio: str | None = Query(default=None),
    data_fim: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Response:
    pdf = generate_company_report_pdf(
        db,
        company_id,
        month=month,
        date_start=data_inicio,
        date_end=data_fim,
    )
    suffix = month or (f"{data_inicio}_{data_fim}" if data_inicio and data_fim else "completo")

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="extrato-cobranca-{company_id}-{suffix}.pdf"'},
    )
