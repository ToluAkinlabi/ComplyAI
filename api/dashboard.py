import json
import os
import re
import csv
import io
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/dashboard/summary")
async def get_dashboard_summary():
    """Get dashboard summary data from all reports"""
    try:
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            return {"total_reports": 0, "recent_reports": [], "summary_stats": {}}
        
        json_files = [f for f in os.listdir(reports_dir) if f.endswith(".json")]
        
        if not json_files:
            return {"total_reports": 0, "recent_reports": [], "summary_stats": {}}
        
        recent_reports = []
        total_aligned = total_weak = total_missing = 0
        framework_stats = {}
        
        # Process up to 10 most recent reports
        for filename in sorted(json_files, reverse=True)[:10]:
            try:
                file_path = os.path.join(reports_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                
                metadata = report_data.get("metadata", {})
                detailed_report = report_data.get("detailed_report", [])
                
                # Count statuses
                aligned_count = len([r for r in detailed_report if r.get("status") == "Aligned"])
                weak_count = len([r for r in detailed_report if r.get("status") == "Weak"])
                missing_count = len([r for r in detailed_report if r.get("status") == "Missing"])
                
                total_aligned += aligned_count
                total_weak += weak_count
                total_missing += missing_count
                
                # Count frameworks
                for rec in detailed_report:
                    framework = rec.get("framework", "Unknown")
                    framework_stats[framework] = framework_stats.get(framework, 0) + 1
                
                # Get file stats
                file_stat = os.stat(file_path)
                
                recent_reports.append({
                    "filename": filename,
                    "client_name": metadata.get("client_name", "Unknown"),
                    "document_name": metadata.get("document_name", "Unknown"),
                    "generated_at": metadata.get("report_generated_at", "Unknown"),
                    "total_sentences": len(detailed_report),
                    "aligned_count": aligned_count,
                    "weak_count": weak_count,
                    "missing_count": missing_count,
                    "file_size": file_stat.st_size,
                    "modified_date": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                })
                
            except Exception as e:
                logger.warning(f"Error processing report {filename}: {e}")
                continue
        
        # Calculate percentages
        total_policy_items = total_aligned + total_weak + total_missing
        alignment_percentage = round((total_aligned / total_policy_items * 100) if total_policy_items > 0 else 0, 1)
        
        summary_stats = {
            "total_policy_items": total_policy_items,
            "total_aligned": total_aligned,
            "total_weak": total_weak,
            "total_missing": total_missing,
            "alignment_percentage": alignment_percentage,
            "top_frameworks": sorted(framework_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        }
        
        return {
            "total_reports": len(json_files),
            "recent_reports": recent_reports,
            "summary_stats": summary_stats
        }
        
    except Exception as e:
        logger.error(f"Error generating dashboard summary: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving dashboard data")

@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get aggregated statistics for dashboard charts"""
    try:
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            return {"framework_distribution": [], "status_trends": [], "recent_activity": []}
        
        json_files = [f for f in os.listdir(reports_dir) if f.endswith(".json")]
        
        framework_counts = {}
        status_counts = {"Aligned": 0, "Weak": 0, "Missing": 0}
        daily_activity = {}
        
        for filename in json_files:
            try:
                file_path = os.path.join(reports_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                
                detailed_report = report_data.get("detailed_report", [])
                metadata = report_data.get("metadata", {})
                
                # Extract date from metadata
                report_date = metadata.get("report_generated_at", "")
                if report_date:
                    try:
                        date_obj = datetime.strptime(report_date, "%Y-%m-%d %H:%M:%S")
                        date_key = date_obj.strftime("%Y-%m-%d")
                        daily_activity[date_key] = daily_activity.get(date_key, 0) + 1
                    except:
                        pass
                
                # Count frameworks and statuses
                for rec in detailed_report:
                    framework = rec.get("framework", "Unknown")
                    status = rec.get("status", "Unknown")
                    
                    framework_counts[framework] = framework_counts.get(framework, 0) + 1
                    if status in status_counts:
                        status_counts[status] += 1
                        
            except Exception as e:
                logger.warning(f"Error processing stats for {filename}: {e}")
                continue
        
        # Format for frontend
        framework_distribution = [
            {"name": framework, "value": count} 
            for framework, count in sorted(framework_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        status_trends = [
            {"name": status, "value": count}
            for status, count in status_counts.items()
        ]
        
        recent_activity = [
            {"date": date, "reports": count}
            for date, count in sorted(daily_activity.items())[-30:]  # Last 30 days
        ]
        
        return {
            "framework_distribution": framework_distribution,
            "status_trends": status_trends,
            "recent_activity": recent_activity
        }
        
    except Exception as e:
        logger.error(f"Error generating dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving dashboard statistics")

@router.get("/reports/{report_name}/json")
async def get_report_json(report_name: str):
    """Get JSON report data"""
    try:
        # Validate filename
        if not re.match(r"^[A-Za-z0-9_.-]+\.json$", report_name):
            raise HTTPException(status_code=400, detail="Invalid report name format")
        
        if ".." in report_name or "/" in report_name or "\\" in report_name:
            raise HTTPException(status_code=400, detail="Invalid report name")
            
        report_path = os.path.join("reports", report_name)
        
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Report not found")

        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
            
        return report_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving JSON report {report_name}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving report data")

@router.get("/reports/{report_name}/csv")
async def export_report_csv(report_name: str):
    """Export report data as CSV"""
    try:
        # Validate filename
        json_name = report_name.replace('.csv', '.json')
        if not re.match(r"^[A-Za-z0-9_.-]+\.json$", json_name):
            raise HTTPException(status_code=400, detail="Invalid report name format")
        
        report_path = os.path.join("reports", json_name)
        
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Report not found")

        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
            
        detailed_report = report_data.get("detailed_report", [])
        
        if not detailed_report:
            raise HTTPException(status_code=404, detail="No data to export")
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Status", "Priority", "Framework", "Control ID", "Section", 
            "Similarity Score", "Policy Statement", "Closest Control", "Suggested Improvement"
        ])
        
        # Write data rows
        for rec in detailed_report:
            writer.writerow([
                rec.get("status", ""),
                rec.get("priority", ""),
                rec.get("framework", ""),
                rec.get("control_id", ""),
                rec.get("section", ""),
                rec.get("similarity_score", ""),
                rec.get("sentence", "").replace('\n', ' ').replace('\r', ' '),
                rec.get("closest_control", "").replace('\n', ' ').replace('\r', ' '),
                rec.get("suggested_improvement", "").replace('\n', ' ').replace('\r', ' ')
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        # Return CSV as downloadable file
        csv_filename = json_name.replace('.json', '.csv')
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={csv_filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting CSV for {report_name}: {e}")
        raise HTTPException(status_code=500, detail="Error exporting CSV")