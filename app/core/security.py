from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    username: str


def _encode_segment(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _decode_segment(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _sign(value: str) -> str:
    signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _encode_segment(signature)


def hash_password(password: str, *, iterations: int = 390000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_encode_segment(salt)}${_encode_segment(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, raw_iterations, salt, raw_digest = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    try:
        iterations = int(raw_iterations)
    except ValueError:
        return False

    expected_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        _decode_segment(salt),
        iterations,
    )
    return hmac.compare_digest(_encode_segment(expected_digest), raw_digest)


def create_access_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": int(time.time()) + (settings.auth_token_expiration_hours * 3600),
    }
    encoded_payload = _encode_segment(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return f"{encoded_payload}.{_sign(encoded_payload)}"


def decode_access_token(token: str) -> AuthenticatedUser:
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso invalido.") from exc

    expected_signature = _sign(encoded_payload)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso invalido.")

    try:
        payload = json.loads(_decode_segment(encoded_payload).decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso invalido.") from exc

    raw_user_id = str(payload.get("sub") or "").strip()
    username = str(payload.get("username") or "").strip()
    expires_at = int(payload.get("exp") or 0)

    if not raw_user_id or not username or expires_at <= int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao expirada. Faca login novamente.")

    try:
        user_id = int(raw_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso invalido.") from exc

    return AuthenticatedUser(user_id=user_id, username=username)


def require_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticacao obrigatoria.")
    return decode_access_token(credentials.credentials)
