import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, select

from database.models import ComplianceReport
from database.session import SessionLocal


def _org_id(user: Optional[Dict[str, Any]]) -> Optional[int]:
    if not user:
        return None
    value = user.get("org_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _user_id(user: Optional[Dict[str, Any]]) -> Optional[int]:
    if not user:
        return None
    value = user.get("user_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def create_report_record(
    *,
    client_name: str,
    document_name: str,
    report_data: Dict[str, Any],
    report_file_name: str,
    json_file_name: str,
    file_size: int,
    processing_time_seconds: float,
    user: Optional[Dict[str, Any]],
) -> Optional[ComplianceReport]:
    with SessionLocal() as db:
        record = ComplianceReport(
            organization_id=_org_id(user),
            created_by_user_id=_user_id(user),
            client_name=client_name,
            document_name=document_name,
            report_data=report_data,
            report_file_name=report_file_name,
            json_file_name=json_file_name,
            status="completed",
            file_size=file_size,
            processing_time=int(round(processing_time_seconds)),
            created_at=datetime.utcnow(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record


def list_report_records_for_user(user: Optional[Dict[str, Any]], include_type: str = "pdf") -> List[ComplianceReport]:
    with SessionLocal() as db:
        stmt = select(ComplianceReport).order_by(ComplianceReport.created_at.desc())
        org_id = _org_id(user)
        if org_id is not None:
            stmt = stmt.where(ComplianceReport.organization_id == org_id)

        if include_type == "pdf":
            stmt = stmt.where(ComplianceReport.report_file_name.is_not(None))
        elif include_type == "json":
            stmt = stmt.where(ComplianceReport.json_file_name.is_not(None))

        return list(db.execute(stmt).scalars().all())


def list_report_history_for_user(
    user: Optional[Dict[str, Any]],
    *,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)

    with SessionLocal() as db:
        base_stmt = select(ComplianceReport)
        count_stmt = select(func.count(ComplianceReport.id))

        org_id = _org_id(user)
        if org_id is not None:
            base_stmt = base_stmt.where(ComplianceReport.organization_id == org_id)
            count_stmt = count_stmt.where(ComplianceReport.organization_id == org_id)

        if status:
            base_stmt = base_stmt.where(ComplianceReport.status == status)
            count_stmt = count_stmt.where(ComplianceReport.status == status)

        if search:
            token = f"%{search.lower()}%"
            search_filter = or_(
                func.lower(ComplianceReport.client_name).like(token),
                func.lower(ComplianceReport.document_name).like(token),
                func.lower(func.coalesce(ComplianceReport.report_file_name, "")).like(token),
                func.lower(func.coalesce(ComplianceReport.json_file_name, "")).like(token),
            )
            base_stmt = base_stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = db.execute(count_stmt).scalar_one()
        rows = db.execute(
            base_stmt.order_by(ComplianceReport.created_at.desc()).offset(safe_offset).limit(safe_limit)
        ).scalars().all()

        items = []
        for record in rows:
            items.append(
                {
                    "id": record.id,
                    "organization_id": record.organization_id,
                    "created_by_user_id": record.created_by_user_id,
                    "client_name": record.client_name,
                    "document_name": record.document_name,
                    "report_file_name": record.report_file_name,
                    "json_file_name": record.json_file_name,
                    "status": record.status,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "file_size": record.file_size,
                    "processing_time": record.processing_time,
                }
            )

        return {
            "items": items,
            "pagination": {
                "limit": safe_limit,
                "offset": safe_offset,
                "total": int(total or 0),
                "has_more": safe_offset + safe_limit < int(total or 0),
            },
        }


def get_report_record_for_user(user: Optional[Dict[str, Any]], report_name: str) -> Optional[ComplianceReport]:
    with SessionLocal() as db:
        stmt = select(ComplianceReport).where(
            (ComplianceReport.report_file_name == report_name)
            | (ComplianceReport.json_file_name == report_name)
        )
        org_id = _org_id(user)
        if org_id is not None:
            stmt = stmt.where(ComplianceReport.organization_id == org_id)

        return db.execute(stmt).scalar_one_or_none()


def delete_report_record_for_user(user: Optional[Dict[str, Any]], report_name: str) -> bool:
    with SessionLocal() as db:
        stmt = select(ComplianceReport).where(
            (ComplianceReport.report_file_name == report_name)
            | (ComplianceReport.json_file_name == report_name)
        )
        org_id = _org_id(user)
        if org_id is not None:
            stmt = stmt.where(ComplianceReport.organization_id == org_id)

        record = db.execute(stmt).scalar_one_or_none()
        if record is None:
            return False

        db.delete(record)
        db.commit()
        return True


def report_path_for_name(report_name: str) -> str:
    return os.path.join("reports", report_name)
