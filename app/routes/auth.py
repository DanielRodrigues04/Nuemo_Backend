from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import AuthenticatedUser, create_access_token, require_access_token
from app.database import get_db
from app.schemas.auth import AuthLoginRequest, AuthLoginResponse, AuthRegisterRequest, AuthUserRead
from app.services.user_service import authenticate_user, create_user, get_user, serialize_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthLoginResponse)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)) -> AuthLoginResponse:
    user = authenticate_user(db, payload.username, payload.password)
    access_token = create_access_token(user.id, user.username)

    return AuthLoginResponse(
        access_token=access_token,
        expires_in_seconds=settings.auth_token_expiration_hours * 3600,
        user=serialize_user(user),
    )


@router.post("/register", response_model=AuthLoginResponse)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)) -> AuthLoginResponse:
    user = create_user(db, payload)
    access_token = create_access_token(user.id, user.username)

    return AuthLoginResponse(
        access_token=access_token,
        expires_in_seconds=settings.auth_token_expiration_hours * 3600,
        user=serialize_user(user),
    )


@router.get("/me", response_model=AuthUserRead)
def read_current_user(
    current_user: AuthenticatedUser = Depends(require_access_token),
    db: Session = Depends(get_db),
) -> AuthUserRead:
    return serialize_user(get_user(db, current_user.user_id))
