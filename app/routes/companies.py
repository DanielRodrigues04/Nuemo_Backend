from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from fastapi import Response

from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services.company_service import create_company, delete_company, get_company_read, list_companies, update_company

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("", response_model=list[CompanyRead])
def get_companies(db: Session = Depends(get_db)) -> list[CompanyRead]:
    return list_companies(db)


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def post_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> CompanyRead:
    return create_company(db, payload)


@router.get("/{company_id}", response_model=CompanyRead)
def get_company_by_id(company_id: int, db: Session = Depends(get_db)) -> CompanyRead:
    return get_company_read(db, company_id)


@router.put("/{company_id}", response_model=CompanyRead)
def put_company(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db)) -> CompanyRead:
    return update_company(db, company_id, payload)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_by_id(company_id: int, db: Session = Depends(get_db)) -> Response:
    delete_company(db, company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
