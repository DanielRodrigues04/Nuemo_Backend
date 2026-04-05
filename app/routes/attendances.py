from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import require_access_token
from app.database import get_db
from app.models.enums import StatusAtendimento
from app.schemas.attendance import AttendanceCreate, AttendancePay, AttendanceRead, AttendanceUpdate
from app.services.attendance_service import (
    create_attendance,
    delete_attendance,
    get_attendance_read,
    list_attendances,
    pay_attendance,
    update_attendance,
)

router = APIRouter(prefix="/attendances", tags=["Attendances"], dependencies=[Depends(require_access_token)])


@router.get("", response_model=list[AttendanceRead])
def get_attendances(
    empresa_id: int | None = Query(default=None, ge=1),
    status_filter: StatusAtendimento | None = Query(default=None, alias="status"),
    data_inicio: str | None = Query(default=None),
    data_fim: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[AttendanceRead]:
    return list_attendances(
        db,
        company_id=empresa_id,
        status=status_filter,
        date_start=data_inicio,
        date_end=data_fim,
    )


@router.post("", response_model=AttendanceRead, status_code=status.HTTP_201_CREATED)
def post_attendance(payload: AttendanceCreate, db: Session = Depends(get_db)) -> AttendanceRead:
    return create_attendance(db, payload)


@router.get("/{attendance_id}", response_model=AttendanceRead)
def get_attendance_by_id(attendance_id: int, db: Session = Depends(get_db)) -> AttendanceRead:
    return get_attendance_read(db, attendance_id)


@router.put("/{attendance_id}", response_model=AttendanceRead)
def put_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
) -> AttendanceRead:
    return update_attendance(db, attendance_id, payload)


@router.patch("/{attendance_id}/pay", response_model=AttendanceRead)
def patch_attendance_pay(
    attendance_id: int,
    payload: AttendancePay,
    db: Session = Depends(get_db),
) -> AttendanceRead:
    return pay_attendance(db, attendance_id, payload)


@router.delete("/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance_by_id(attendance_id: int, db: Session = Depends(get_db)) -> Response:
    delete_attendance(db, attendance_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
