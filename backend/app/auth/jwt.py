from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header
from psycopg import Connection

from app.db import get_conn
from app.errors import AppError, forbidden
from app.settings import get_settings


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    role: str  # user | researcher | admin — from profiles, never from the token

    @property
    def is_staff(self) -> bool:
        return self.role in ("researcher", "admin")


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(get_settings().jwks_url, cache_keys=True, lifespan=3600)


def verify_token(token: str, key=None, issuer: str | None = None) -> UUID:
    """Validate a Supabase access token (ES256 via JWKS; iss, aud, exp, sub). Returns the user id."""
    try:
        if key is None:
            key = _jwks_client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=issuer or get_settings().jwt_issuer,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
        return UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError) as e:
        raise AppError(401, "invalid_token", str(e)) from e


def current_user(
    conn: Annotated[Connection, Depends(get_conn)],
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "missing_token")
    uid = verify_token(authorization[7:].strip())
    row = conn.execute("select role from public.profiles where id = %s", (uid,)).fetchone()
    if not row:
        raise AppError(401, "unknown_user")
    return CurrentUser(uid, row["role"])


User = Annotated[CurrentUser, Depends(current_user)]


def require_staff(user: User) -> CurrentUser:
    if not user.is_staff:
        raise forbidden()
    return user


def require_admin(user: User) -> CurrentUser:
    if user.role != "admin":
        raise forbidden()
    return user


Staff = Annotated[CurrentUser, Depends(require_staff)]
Admin = Annotated[CurrentUser, Depends(require_admin)]
