from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from fastapi import Response

from app.schemas.exam import ExamCreate, ExamRead, ExamUpdate
from app.services.exam_service import create_exam, delete_exam, get_exam_read, list_exams, update_exam

router = APIRouter(prefix="/exams", tags=["Exams"])


@router.get("", response_model=list[ExamRead])
def get_exams(db: Session = Depends(get_db)) -> list[ExamRead]:
    return list_exams(db)


@router.post("", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
def post_exam(payload: ExamCreate, db: Session = Depends(get_db)) -> ExamRead:
    return create_exam(db, payload)


@router.get("/{exam_id}", response_model=ExamRead)
def get_exam_by_id(exam_id: int, db: Session = Depends(get_db)) -> ExamRead:
    return get_exam_read(db, exam_id)


@router.put("/{exam_id}", response_model=ExamRead)
def put_exam(exam_id: int, payload: ExamUpdate, db: Session = Depends(get_db)) -> ExamRead:
    return update_exam(db, exam_id, payload)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam_by_id(exam_id: int, db: Session = Depends(get_db)) -> Response:
    delete_exam(db, exam_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
