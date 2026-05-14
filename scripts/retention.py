import os
from datetime import datetime, timedelta
from typing import Dict, cast

from sqlalchemy import select

from database.models import ComplianceReport
from database.session import SessionLocal
from database.report_store import report_path_for_name


def retention_window_days() -> int:
    value = os.getenv("REPORT_RETENTION_DAYS", "365")
    try:
        parsed = int(value)
    except ValueError:
        parsed = 365
    return max(1, parsed)


def purge_expired_reports(*, now: datetime | None = None) -> Dict[str, int]:
    current_time = now or datetime.utcnow()
    cutoff = current_time - timedelta(days=retention_window_days())

    deleted_records = 0
    deleted_files = 0

    with SessionLocal() as db:
        rows = list(db.execute(select(ComplianceReport).where(ComplianceReport.created_at < cutoff)).scalars().all())
        for record in rows:
            filenames = [record.report_file_name, record.json_file_name]
            for name in filenames:
                if not name:
                    continue
                path = report_path_for_name(str(name))
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        deleted_files += 1
                    except OSError:
                        pass

            db.delete(record)
            deleted_records += 1

        db.commit()

    return {
        "deleted_records": deleted_records,
        "deleted_files": deleted_files,
    }
