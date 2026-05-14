import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, cast

from fastapi import HTTPException
from sqlalchemy import select

from database.models import PasswordResetToken, User
from database.session import SessionLocal
from scripts.auth import hash_password


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(*, email: str, ttl_minutes: int = 30) -> Optional[str]:
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Email is required")

    with SessionLocal() as db:
        user = cast(Any, db.execute(select(User).where(User.email == normalized_email, User.is_active.is_(True))).scalar_one_or_none())
        if user is None:
            # Do not reveal whether the account exists.
            return None

        raw_token = secrets.token_urlsafe(36)
        token_hash = _hash_token(raw_token)

        reset = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
            used_at=None,
        )
        db.add(reset)
        db.commit()

        return raw_token


def consume_password_reset_token(*, token: str, new_password: str) -> Dict[str, Any]:
    token_hash = _hash_token(token)
    now = datetime.utcnow()

    with SessionLocal() as db:
        reset = cast(Any, db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)).scalar_one_or_none())
        if reset is None or reset.used_at is not None or reset.expires_at <= now:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        user = cast(Any, db.execute(select(User).where(User.id == reset.user_id, User.is_active.is_(True))).scalar_one_or_none())
        if user is None:
            raise HTTPException(status_code=400, detail="Reset token is no longer valid")

        user.hashed_password = hash_password(new_password)
        reset.used_at = now
        db.commit()

        return {
            "email": str(user.email),
            "user_id": int(user.id),
        }
