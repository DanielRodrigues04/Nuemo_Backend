from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.exam import Exame
from app.schemas.exam import ExamCreate, ExamRead, ExamUpdate
from app.services.serializers import serialize_exam


def list_exams(db: Session) -> list[ExamRead]:
    exams = db.scalars(select(Exame).order_by(Exame.nome.asc())).all()
    return [serialize_exam(exam) for exam in exams]


def get_exam(db: Session, exam_id: int) -> Exame:
    exam = db.get(Exame, exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exame nao encontrado.")
    return exam


def get_exam_read(db: Session, exam_id: int) -> ExamRead:
    return serialize_exam(get_exam(db, exam_id))


def ensure_exam_name_available(db: Session, name: str, exam_id: int | None = None) -> None:
    query = select(Exame).where(func.lower(Exame.nome) == name.lower())
    if exam_id is not None:
        query = query.where(Exame.id != exam_id)

    existing = db.scalar(query)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ja existe um exame com esse nome.")


def create_exam(db: Session, payload: ExamCreate) -> ExamRead:
    normalized_name = payload.nome.strip()
    ensure_exam_name_available(db, normalized_name)

    exam = Exame(nome=normalized_name, valor=Decimal(str(payload.valor)))
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return serialize_exam(exam)


def update_exam(db: Session, exam_id: int, payload: ExamUpdate) -> ExamRead:
    exam = get_exam(db, exam_id)
    normalized_name = payload.nome.strip()
    ensure_exam_name_available(db, normalized_name, exam_id=exam_id)

    exam.nome = normalized_name
    exam.valor = Decimal(str(payload.valor))

    db.add(exam)
    db.commit()
    db.refresh(exam)
    return serialize_exam(exam)


def delete_exam(db: Session, exam_id: int) -> None:
    exam = get_exam(db, exam_id)

    try:
        db.delete(exam)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nao e possivel excluir o exame porque existem atendimentos vinculados.",
        ) from exc
