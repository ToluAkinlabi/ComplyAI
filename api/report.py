import os
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
import logging
from scripts.auth import require_authenticated_user_if_enabled
from database.report_store import (
    delete_report_record_for_user,
    get_report_record_for_user,
    list_report_history_for_user,
    list_report_records_for_user,
    report_path_for_name,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _list_reports_from_filesystem(extension: str):
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        return []

    files = []
    for filename in os.listdir(reports_dir):
        if not filename.endswith(extension):
            continue
        file_path = os.path.join(reports_dir, filename)
        try:
            stat = os.stat(file_path)
            files.append({
                "name": filename,
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "size_kb": round(stat.st_size / 1024, 2),
                "modified": stat.st_mtime,
                "modified_date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
        except OSError:
            continue
    files.sort(key=lambda x: x["modified"], reverse=True)
    return files

@router.get("/list-reports/")
async def list_reports(request: Request):
    """List all PDF reports with enhanced metadata"""
    current_user = require_authenticated_user_if_enabled(request)
    
    try:
        records = list_report_records_for_user(current_user, include_type="pdf")
        files = []
        for record in records:
            if not record.report_file_name:
                continue
            file_path = report_path_for_name(record.report_file_name)
            modified = record.created_at.timestamp() if record.created_at else 0
            if os.path.exists(file_path):
                try:
                    modified = os.stat(file_path).st_mtime
                except OSError:
                    pass
            files.append({
                "name": record.report_file_name,
                "size": record.file_size or 0,
                "size_mb": round((record.file_size or 0) / (1024 * 1024), 2),
                "modified": modified,
                "modified_date": datetime.fromtimestamp(modified).strftime("%Y-%m-%d %H:%M:%S") if modified else "Unknown",
            })

        if not files and current_user is None:
            files = _list_reports_from_filesystem(".pdf")

        files.sort(key=lambda x: x.get("modified", 0), reverse=True)
        return {"reports": files, "total_count": len(files)}
    
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving reports list")

@router.get("/list-json-reports/")
async def list_json_reports(request: Request):
    """List all JSON reports for dashboard with metadata"""
    current_user = require_authenticated_user_if_enabled(request)
    
    try:
        records = list_report_records_for_user(current_user, include_type="json")
        files = []
        for record in records:
            if not record.json_file_name:
                continue
            file_path = report_path_for_name(record.json_file_name)
            modified = record.created_at.timestamp() if record.created_at else 0
            size = 0
            if os.path.exists(file_path):
                try:
                    stat = os.stat(file_path)
                    modified = stat.st_mtime
                    size = stat.st_size
                except OSError:
                    pass
            files.append({
                "name": record.json_file_name,
                "size": size,
                "size_kb": round(size / 1024, 2),
                "modified": modified,
                "modified_date": datetime.fromtimestamp(modified).strftime("%Y-%m-%d %H:%M:%S") if modified else "Unknown",
            })

        if not files and current_user is None:
            files = _list_reports_from_filesystem(".json")

        files.sort(key=lambda x: x.get("modified", 0), reverse=True)
        return {"reports": files, "total_count": len(files)}
    
    except Exception as e:
        logger.error(f"Error listing JSON reports: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving JSON reports list")

@router.get("/reports/history")
async def list_report_history(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    """List org-scoped report history with pagination and optional search/status filters."""
    current_user = require_authenticated_user_if_enabled(request)

    try:
        history = list_report_history_for_user(
            current_user,
            limit=limit,
            offset=offset,
            search=search,
            status=status,
        )
        return history
    except Exception as e:
        logger.error(f"Error listing report history: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving report history")


@router.delete("/delete-report/{report_name}")
async def delete_report(report_name: str, request: Request):
    """Delete a report and its associated JSON file with validation"""
    current_user = require_authenticated_user_if_enabled(request)
    try:
        # Enhanced filename validation
        if not re.match(r"^[A-Za-z0-9_.-]+\.(pdf|json)$", report_name):
            raise HTTPException(status_code=400, detail="Invalid report name format")
        
        # Additional security check - prevent directory traversal
        if ".." in report_name or "/" in report_name or "\\" in report_name:
            raise HTTPException(status_code=400, detail="Invalid report name - contains path separators")
            
        record = get_report_record_for_user(current_user, report_name)
        if current_user is not None and record is None:
            raise HTTPException(status_code=404, detail="Report not found")

        report_path = report_path_for_name(report_name)
        
        # Ensure path is within reports directory
        reports_dir = os.path.abspath("reports")
        abs_report_path = os.path.abspath(report_path)
        
        try:
            common_path = os.path.commonpath([reports_dir, abs_report_path])
            if common_path != reports_dir:
                raise HTTPException(status_code=400, detail="Invalid report path")
        except ValueError:
            # Different drives on Windows
            raise HTTPException(status_code=400, detail="Invalid report path")

        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Report not found")

        # Delete the requested file
        try:
            os.remove(report_path)
            logger.info(f"Deleted report: {report_name}")
        except OSError as e:
            logger.error(f"Failed to delete {report_name}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete report file")
        
        # Also delete the associated file (PDF→JSON or JSON→PDF)
        associated_file = None
        if record is not None:
            if report_name == record.report_file_name:
                associated_file = record.json_file_name
            elif report_name == record.json_file_name:
                associated_file = record.report_file_name
        if associated_file is None:
            base_name = os.path.splitext(report_name)[0]
            associated_file = f"{base_name}.json" if report_name.endswith(".pdf") else f"{base_name}.pdf"
            
        associated_path = report_path_for_name(associated_file)
        if os.path.exists(associated_path):
            try:
                os.remove(associated_path)
                logger.info(f"Deleted associated file: {associated_file}")
            except OSError as e:
                logger.warning(f"Failed to delete associated file {associated_file}: {e}")

        delete_report_record_for_user(current_user, report_name)

        return {"success": True, "detail": "Report deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report {report_name}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting report")


@router.get("/reports/{report_name}")
async def download_report(report_name: str, request: Request):
    """Download PDF or JSON report file with filename validation."""
    current_user = require_authenticated_user_if_enabled(request)

    if not re.match(r"^[A-Za-z0-9_.-]+\.(pdf|json)$", report_name):
        raise HTTPException(status_code=400, detail="Invalid report name format")

    if ".." in report_name or "/" in report_name or "\\" in report_name:
        raise HTTPException(status_code=400, detail="Invalid report name")

    record = get_report_record_for_user(current_user, report_name)
    if current_user is not None and record is None:
        raise HTTPException(status_code=404, detail="Report not found")

    report_path = report_path_for_name(report_name)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")

    media_type = "application/pdf" if report_name.endswith(".pdf") else "application/json"
    return FileResponse(report_path, media_type=media_type, filename=report_name)