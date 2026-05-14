import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import func, select

from database.models import ComplianceReport
from database.session import SessionLocal


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _next_month_start(dt: datetime) -> datetime:
    if dt.month == 12:
        return datetime(year=dt.year + 1, month=1, day=1)
    return datetime(year=dt.year, month=dt.month + 1, day=1)


def get_monthly_report_usage(org_id: int, now: Optional[datetime] = None) -> int:
    current = now or datetime.utcnow()
    start = datetime(year=current.year, month=current.month, day=1)
    end = _next_month_start(start)

    with SessionLocal() as db:
        stmt = select(func.count(ComplianceReport.id)).where(
            ComplianceReport.organization_id == org_id,
            ComplianceReport.created_at >= start,
            ComplianceReport.created_at < end,
        )
        return int(db.execute(stmt).scalar_one() or 0)


def enforce_monthly_report_limit(user: Optional[Dict[str, Any]]) -> None:
    raw_limit = os.getenv("MONTHLY_REPORT_LIMIT_PER_ORG", "0")
    try:
        limit = int(raw_limit)
    except ValueError:
        limit = 0

    if limit <= 0:
        return

    org_id = _as_int((user or {}).get("org_id"))
    if org_id is None:
        return

    usage = get_monthly_report_usage(org_id)
    if usage >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly report quota reached for organization ({usage}/{limit}).",
        )


def get_usage_snapshot(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    raw_limit = os.getenv("MONTHLY_REPORT_LIMIT_PER_ORG", "0")
    try:
        limit = int(raw_limit)
    except ValueError:
        limit = 0

    org_id = _as_int((user or {}).get("org_id"))
    used = get_monthly_report_usage(org_id) if org_id is not None else 0
    is_limited = limit > 0
    remaining = max(0, limit - used) if is_limited else None
    usage_percent = round((used / limit) * 100, 2) if is_limited and limit > 0 else None

    return {
        "organization_id": org_id,
        "monthly_limit": limit,
        "used": used,
        "remaining": remaining,
        "is_limited": is_limited,
        "usage_percent": usage_percent,
    }
