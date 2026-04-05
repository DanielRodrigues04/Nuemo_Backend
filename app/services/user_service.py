from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import Usuario
from app.schemas.auth import AuthRegisterRequest, AuthUserRead


def normalize_username(value: str) -> str:
    return value.strip().lower()


def build_user_query() -> Select[tuple[Usuario]]:
    return select(Usuario)


def serialize_user(user: Usuario) -> AuthUserRead:
    return AuthUserRead(
        id=user.id,
        nome=user.nome,
        username=user.username,
        created_at=user.created_at,
    )


def get_user_by_username(db: Session, username: str) -> Usuario | None:
    normalized = normalize_username(username)
    return db.scalar(build_user_query().where(Usuario.username == normalized))


def get_user(db: Session, user_id: int) -> Usuario:
    user = db.scalar(build_user_query().where(Usuario.id == user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")
    return user


def authenticate_user(db: Session, username: str, password: str) -> Usuario:
    user = get_user_by_username(db, username)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login ou senha invalidos.")
    return user


def create_user(db: Session, payload: AuthRegisterRequest) -> Usuario:
    normalized_username = normalize_username(payload.username)

    if get_user_by_username(db, normalized_username) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ja existe um usuario com esse login.")

    user = Usuario(
        nome=payload.nome.strip() if payload.nome else None,
        username=normalized_username,
        password_hash=hash_password(payload.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
