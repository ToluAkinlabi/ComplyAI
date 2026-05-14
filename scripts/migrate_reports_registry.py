import argparse
import json
import os
from datetime import datetime

from sqlalchemy import select

from database.models import ComplianceReport
from database.session import SessionLocal, init_database
from scripts.auth import DEFAULT_ADMIN_EMAIL, get_user_claims, init_auth_storage


def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def migrate_reports(reports_dir: str, dry_run: bool = False) -> int:
    if not os.path.isdir(reports_dir):
        print(f"Reports directory not found: {reports_dir}")
        return 0

    init_database()
    init_auth_storage()
    actor = get_user_claims(DEFAULT_ADMIN_EMAIL) or {}

    json_files = [f for f in os.listdir(reports_dir) if f.endswith(".json")]
    migrated = 0

    with SessionLocal() as db:
        for json_name in sorted(json_files):
            base_name = os.path.splitext(json_name)[0]
            pdf_name = f"{base_name}.pdf"

            exists_stmt = select(ComplianceReport).where(
                (ComplianceReport.json_file_name == json_name)
                | (ComplianceReport.report_file_name == pdf_name)
            )
            existing = db.execute(exists_stmt).scalar_one_or_none()
            if existing is not None:
                continue

            json_path = os.path.join(reports_dir, json_name)
            pdf_path = os.path.join(reports_dir, pdf_name)

            payload = load_json(json_path)
            metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}

            created_at = datetime.utcnow()
            generated_at = metadata.get("report_generated_at")
            if generated_at:
                try:
                    created_at = datetime.strptime(generated_at, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

            file_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
            processing_time = metadata.get("processing_time_seconds") or 0
            try:
                processing_time = int(round(float(processing_time)))
            except Exception:
                processing_time = 0

            record = ComplianceReport(
                organization_id=actor.get("org_id"),
                created_by_user_id=actor.get("user_id"),
                client_name=metadata.get("client_name", "Unknown"),
                document_name=metadata.get("document_name", "Unknown"),
                report_data=payload if isinstance(payload, dict) else {},
                report_file_name=pdf_name if os.path.exists(pdf_path) else None,
                json_file_name=json_name,
                status="completed",
                created_at=created_at,
                file_size=file_size,
                processing_time=processing_time,
            )

            db.add(record)
            migrated += 1

        if not dry_run:
            db.commit()

    return migrated


def main():
    parser = argparse.ArgumentParser(description="Backfill report registry records from reports folder")
    parser.add_argument("--reports-dir", default="reports", help="Path to reports directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without committing")
    args = parser.parse_args()

    count = migrate_reports(args.reports_dir, dry_run=args.dry_run)
    mode = "Would migrate" if args.dry_run else "Migrated"
    print(f"{mode} {count} report records")


if __name__ == "__main__":
    main()
