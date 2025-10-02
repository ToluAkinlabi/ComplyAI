import os
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/list-reports/")
async def list_reports():
    """List all PDF reports with enhanced metadata"""
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        return {"reports": [], "total_count": 0}
    
    try:
        files = []
        for f in os.listdir(reports_dir):
            if f.endswith(".pdf"):
                file_path = os.path.join(reports_dir, f)
                try:
                    stat = os.stat(file_path)
                    files.append({
                        "name": f,
                        "size": stat.st_size,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "modified": stat.st_mtime,
                        "modified_date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
                except OSError:
                    continue

        files.sort(key=lambda x: x["modified"], reverse=True)
        return {"reports": files, "total_count": len(files)}
    
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving reports list")

@router.get("/list-json-reports/")
async def list_json_reports():
    """List all JSON reports for dashboard with metadata"""
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        return {"reports": [], "total_count": 0}
    
    try:
        files = []
        for f in os.listdir(reports_dir):
            if f.endswith(".json"):
                file_path = os.path.join(reports_dir, f)
                try:
                    stat = os.stat(file_path)
                    files.append({
                        "name": f,
                        "size": stat.st_size,
                        "size_kb": round(stat.st_size / 1024, 2),
                        "modified": stat.st_mtime,
                        "modified_date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
                except OSError:
                    continue

        files.sort(key=lambda x: x["modified"], reverse=True)
        return {"reports": files, "total_count": len(files)}
    
    except Exception as e:
        logger.error(f"Error listing JSON reports: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving JSON reports list")

@router.delete("/delete-report/{report_name}")
async def delete_report(report_name: str):
    """Delete a report and its associated JSON file with validation"""
    try:
        # Enhanced filename validation
        if not re.match(r"^[A-Za-z0-9_.-]+\.(pdf|json)$", report_name):
            raise HTTPException(status_code=400, detail="Invalid report name format")
        
        # Additional security check - prevent directory traversal
        if ".." in report_name or "/" in report_name or "\\" in report_name:
            raise HTTPException(status_code=400, detail="Invalid report name - contains path separators")
            
        report_path = os.path.join("reports", report_name)
        
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
        base_name = os.path.splitext(report_name)[0]
        if report_name.endswith(".pdf"):
            associated_file = f"{base_name}.json"
        else:
            associated_file = f"{base_name}.pdf"
            
        associated_path = os.path.join("reports", associated_file)
        if os.path.exists(associated_path):
            try:
                os.remove(associated_path)
                logger.info(f"Deleted associated file: {associated_file}")
            except OSError as e:
                logger.warning(f"Failed to delete associated file {associated_file}: {e}")

        return {"success": True, "detail": "Report deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report {report_name}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting report")