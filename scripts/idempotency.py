import hashlib
from datetime import datetime
from typing import Any, Dict, Optional, cast

from sqlalchemy import select

from database.models import UploadIdempotencyKey
from database.session import SessionLocal


SCOPE_ANONYMOUS_USER = -1


def _fingerprint(client_name: str, filename: str) -> str:
    payload = f"{client_name.strip().lower()}::{filename.strip().lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _scope(user: Optional[Dict[str, Any]]) -> tuple[Optional[int], int]:
    if not user:
        return None, SCOPE_ANONYMOUS_USER

    org_id = user.get("org_id")
    user_id = user.get("user_id")
    try:
        parsed_org = int(org_id) if org_id is not None else None
    except (TypeError, ValueError):
        parsed_org = None

    try:
        parsed_user = int(user_id) if user_id is not None else SCOPE_ANONYMOUS_USER
    except (TypeError, ValueError):
        parsed_user = SCOPE_ANONYMOUS_USER

    return parsed_org, parsed_user


def get_cached_upload_response(*, idempotency_key: str, client_name: str, filename: str, user: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    org_id, user_id = _scope(user)
    expected = _fingerprint(client_name, filename)

    with SessionLocal() as db:
        record = cast(Any, db.execute(
            select(UploadIdempotencyKey).where(
                UploadIdempotencyKey.organization_id == org_id,
                UploadIdempotencyKey.user_id == user_id,
                UploadIdempotencyKey.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none())

        if record is None:
            return None

        if str(record.request_fingerprint) != expected:
            raise ValueError("Idempotency key was already used with a different request payload")

        if record.status == "completed" and isinstance(record.response_payload, dict):
            return cast(Dict[str, Any], record.response_payload)

        return None


def store_upload_response(*, idempotency_key: str, client_name: str, filename: str, user: Optional[Dict[str, Any]], response_payload: Dict[str, Any]) -> None:
    org_id, user_id = _scope(user)
    expected = _fingerprint(client_name, filename)

    with SessionLocal() as db:
        record = cast(Any, db.execute(
            select(UploadIdempotencyKey).where(
                UploadIdempotencyKey.organization_id == org_id,
                UploadIdempotencyKey.user_id == user_id,
                UploadIdempotencyKey.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none())

        if record is None:
            record = UploadIdempotencyKey(
                organization_id=org_id,
                user_id=user_id,
                idempotency_key=idempotency_key,
                request_fingerprint=expected,
                response_payload=response_payload,
                status="completed",
                completed_at=datetime.utcnow(),
            )
            db.add(record)
            db.commit()
            return

        if str(record.request_fingerprint) != expected:
            raise ValueError("Idempotency key was already used with a different request payload")

        record.response_payload = response_payload
        record.status = "completed"
        record.completed_at = datetime.utcnow()
        db.commit()
