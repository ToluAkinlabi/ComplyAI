from datetime import datetime
from typing import Any, Dict, Optional

from database.models import AuditLog
from database.session import SessionLocal


def write_audit_log(
    *,
    organization_id: Optional[int],
    user_id: Optional[int],
    event_type: str,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    status: str = "success",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        with SessionLocal() as db:
            entry = AuditLog(
                organization_id=organization_id,
                user_id=user_id,
                event_type=event_type,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                details=details or {},
                created_at=datetime.utcnow(),
            )
            db.add(entry)
            db.commit()
    except Exception:
        # Audit logging should never block the request lifecycle.
        return
