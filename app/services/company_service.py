from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.company import Empresa
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services.serializers import serialize_company


def list_companies(db: Session) -> list[CompanyRead]:
    companies = db.scalars(select(Empresa).order_by(Empresa.nome.asc())).all()
    return [serialize_company(company) for company in companies]


def get_company(db: Session, company_id: int) -> Empresa:
    company = db.get(Empresa, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa nao encontrada.")
    return company


def get_company_read(db: Session, company_id: int) -> CompanyRead:
    return serialize_company(get_company(db, company_id))


def ensure_company_name_available(db: Session, name: str, company_id: int | None = None) -> None:
    query = select(Empresa).where(func.lower(Empresa.nome) == name.lower())
    if company_id is not None:
        query = query.where(Empresa.id != company_id)

    existing = db.scalar(query)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ja existe uma empresa com esse nome.")


def ensure_company_document_available(db: Session, document: str | None, company_id: int | None = None) -> None:
    if not document:
        return

    query = select(Empresa).where(Empresa.documento == document)
    if company_id is not None:
        query = query.where(Empresa.id != company_id)

    existing = db.scalar(query)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ja existe uma empresa com esse documento.")


def create_company(db: Session, payload: CompanyCreate) -> CompanyRead:
    normalized_name = payload.nome.strip()
    ensure_company_name_available(db, normalized_name)
    ensure_company_document_available(db, payload.documento)

    company = Empresa(
        nome=normalized_name,
        tipo=payload.tipo,
        documento=payload.documento,
        contato=payload.contato,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return serialize_company(company)


def update_company(db: Session, company_id: int, payload: CompanyUpdate) -> CompanyRead:
    company = get_company(db, company_id)
    normalized_name = payload.nome.strip()
    ensure_company_name_available(db, normalized_name, company_id=company_id)
    ensure_company_document_available(db, payload.documento, company_id=company_id)

    company.nome = normalized_name
    company.tipo = payload.tipo
    company.documento = payload.documento
    company.contato = payload.contato

    db.add(company)
    db.commit()
    db.refresh(company)
    return serialize_company(company)


def delete_company(db: Session, company_id: int) -> None:
    company = get_company(db, company_id)

    try:
        db.delete(company)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nao e possivel excluir a empresa porque existem atendimentos vinculados.",
        ) from exc
