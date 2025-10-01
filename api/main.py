"""
FastAPI application for ComplyAI - Compliance document analysis and framework matching
"""

# CORS and Security imports
from scripts.cors import setup_cors
from scripts.security_hardening import apply_owasp_hardening

# FastAPI imports
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

# Standard library imports
import logging
import json
import shutil
import os
from datetime import datetime
from contextlib import asynccontextmanager

# Third-party imports
from loguru import logger
from jose import jwt, JWTError

# Local imports
from scripts import docparser, recommendation_engine, pdf_exporter
from scripts.semantic_engine import semantic_engine, is_valid_sentence, group_semantic_sentences
from scripts.framework_loader import load_frameworks  # Fixed: Added missing import
from scripts.auth import (
    users_db,
    verify_password,
    create_access_token,
    admin_required,
)
from scripts.prod_settings import settings
import scripts.logger_config

# Environment check
if os.getenv("ENV") == "production":
    raise HTTPException(status_code=403, detail="Forbidden in production")

# Global variables for framework data
framework_index = None
framework_sentences = []
framework_labels = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management - initialize semantic engine on startup"""
    global framework_index, framework_sentences, framework_labels
    try:
        print("🚀 Starting ComplyAI...")
        
        # Load frameworks
        fw_data = load_frameworks()
        
        # Build enhanced index - returns (index, chunks_metadata)
        index, chunks_metadata = semantic_engine.build_enhanced_index(fw_data)
        
        # Store for global access
        framework_index = index
        framework_sentences = [chunk.text for chunk in chunks_metadata]
        framework_labels = [chunk.framework_name for chunk in chunks_metadata]
        
        print("✅ ComplyAI initialized successfully!")
        yield
    except Exception as e:
        print(f"❌ Failed to initialize ComplyAI: {e}")
        raise

# Initialize FastAPI app
app = FastAPI(
    title="ComplyAI",
    description="Compliance document analysis and framework matching API",
    version="2.0.0",
    lifespan=lifespan
)

# Setup CORS and security
setup_cors(app)
apply_owasp_hardening(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

# Create necessary directories
os.makedirs("data/uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# Serve reports folder
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """User authentication endpoint"""
    logger.info(f"Login attempt for user: {form_data.username}")

    user = users_db.get(form_data.username)
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user["email"], "role": user["role"]})
    logger.info(f"Successful login for user: {form_data.username}")
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/upload-policy/")
async def upload_policy(file: UploadFile = File(...), client_name: str = Form(...)):
    try:
        if not file.filename.endswith((".pdf", ".docx")):
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF or DOCX files.")

        file_path = f"data/uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Processing file: {file.filename} for client: {client_name}")

        policy_sentences = docparser.extract_policy_sentences(file_path)
        if not policy_sentences:
            raise HTTPException(status_code=400, detail="No valid policy content found in the document.")

        # Filter & group (with fallback to avoid wiping everything)
        cleaned = [s for s in policy_sentences if is_valid_sentence(s)]
        if not cleaned:
            # fallback: keep lines > 30 chars to ensure we have something
            cleaned = [s for s in policy_sentences if len(s.strip()) > 30]

        grouped_sentences = group_semantic_sentences(cleaned, threshold=0.7)
        if not grouped_sentences:
            grouped_sentences = cleaned  # final fallback

        logger.info(f"Extracted {len(policy_sentences)} raw lines; {len(grouped_sentences)} semantic groups.")

        recommendations = recommendation_engine.generate_recommendations(grouped_sentences)
        if not recommendations:
            raise HTTPException(status_code=400, detail="Unable to generate recommendations from the policy document.")

        executive_summary = recommendation_engine.generate_executive_summary(recommendations)

        report_data = {
            "executive_summary": executive_summary,
            "detailed_report": recommendations,
            "metadata": {
                "client_name": client_name,
                "document_name": file.filename,
                "total_sentences": len(policy_sentences),
                "processed_sentences": len(grouped_sentences),
                "total_recommendations": len(recommendations),
                "report_generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

        output_path = pdf_exporter.export_pdf(report_data, client_name)

        json_filename = f"{client_name.replace(' ', '_')}_Compliance_Report.json"
        json_path = f"reports/{json_filename}"
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(report_data, jf, indent=2, ensure_ascii=False)

        os.remove(file_path)
        logger.info(f"Successfully generated report for {client_name}: {output_path}")

        return {
            "success": True,
            "message": "Policy analysis completed successfully",
            "executive_summary": executive_summary,
            "total_recommendations": len(recommendations),
            "report_url": f"/reports/{os.path.basename(output_path)}",
            "json_report_url": f"/reports/{json_filename}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing policy upload: {e}", exc_info=True)
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="An error occurred while processing the document.")

@app.get("/list-reports/")
async def list_reports():
    """List all PDF reports"""
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        return {"reports": []}
    
    try:
        files = []
        for f in os.listdir(reports_dir):
            if f.endswith(".pdf"):
                file_path = os.path.join(reports_dir, f)
                files.append({
                    "name": f,
                    "size": os.path.getsize(file_path),
                    "modified": os.path.getmtime(file_path)
                })

        # Sort by latest modified date
        files.sort(key=lambda x: x["modified"], reverse=True)
        return {"reports": files}
    
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving reports list")

@app.get("/list-json-reports/")
async def list_json_reports():
    """List all JSON reports for dashboard"""
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        return {"reports": []}
    
    try:
        files = []
        for f in os.listdir(reports_dir):
            if f.endswith(".json"):
                file_path = os.path.join(reports_dir, f)
                files.append({
                    "name": f,
                    "size": os.path.getsize(file_path),
                    "modified": os.path.getmtime(file_path)
                })

        # Sort by latest modified date
        files.sort(key=lambda x: x["modified"], reverse=True)
        return {"reports": files}
    
    except Exception as e:
        logger.error(f"Error listing JSON reports: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving JSON reports list")

@app.delete("/delete-report/{report_name}")
async def delete_report(report_name: str):
    """Delete a report and its associated JSON file"""
    try:
        report_path = f"reports/{report_name}"
        
        # Also delete the associated JSON file
        json_name = report_name.rsplit('.', 1)[0] + ".json"
        json_path = f"reports/{json_name}"

        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Report not found")

        # Delete PDF report
        os.remove(report_path)
        logger.info(f"Deleted PDF report: {report_name}")
        
        # Delete JSON file if it exists
        if os.path.exists(json_path):
            os.remove(json_path)
            logger.info(f"Deleted JSON report: {json_name}")

        return {"detail": "Report and associated JSON deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report {report_name}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting report")

@app.post("/rebuild-index/")
async def rebuild_index(request: Request, user=Depends(admin_required)):
    """Rebuild the semantic search index (Admin only)"""
    try:
        global framework_index, framework_sentences, framework_labels
        
        logger.info(f"🔁 Rebuilding semantic index triggered by admin from {request.client.host}")
        
        # Reload frameworks and rebuild index
        fw_data = load_frameworks()
        index, chunks_metadata = semantic_engine.build_enhanced_index(fw_data)
        
        # Update global variables
        framework_index = index
        framework_sentences = [chunk.text for chunk in chunks_metadata]
        framework_labels = [chunk.framework_name for chunk in chunks_metadata]

        logger.info("✅ Semantic index rebuilt successfully")
        return {"detail": "Semantic index rebuilt successfully"}
        
    except Exception as e:
        logger.error(f"❌ Failed to rebuild index: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to rebuild semantic index")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "semantic_engine_ready": framework_index is not None,
        "total_framework_chunks": len(framework_sentences) if framework_sentences else 0
    }

# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP Error {exc.status_code} | {exc.detail} | From {request.client.host}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "success": False}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation Error | {exc} | From {request.client.host}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid input",
            "details": exc.errors(),
            "success": False
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception | {exc} | Path: {request.url.path} | Client: {request.client.host}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred",
            "success": False
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )