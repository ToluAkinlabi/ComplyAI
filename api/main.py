"""
FastAPI application for ComplyAI - Compliance document analysis and framework matching
"""

# Standard library imports
import json
import re
import os
import sys
import platform
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional
import tempfile
import asyncio 

# FastAPI imports
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

# CORS and Security imports
from scripts.cors import setup_cors
from scripts.security_hardening import apply_owasp_hardening

# Local imports
from scripts import docparser, recommendation_engine, pdf_exporter
from scripts.semantic_engine import semantic_engine, is_valid_sentence, group_semantic_sentences
from scripts.framework_loader import load_frameworks
from scripts.auth import users_db, verify_password, create_access_token, admin_required

# Import route modules
from api.dashboard import router as dashboard_router
from api.report import router as report_router

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Global variables for framework data
class AppState:
    def __init__(self):
        self.framework_index = None
        self.framework_sentences = []
        self.framework_labels = []
        self.app_initialized = False
        self.initialization_error = None

app_state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global framework_index, framework_sentences, framework_labels, app_initialized, initialization_error
    
    try:
        logger.info("🚀 Starting ComplyAI initialization...")
        
        # Validate environment
        required_env_vars = ["OPENAI_API_KEY", "OPENAI_MODEL"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            error_msg = f"Missing required environment variables: {missing_vars}"
            logger.error(error_msg)
            initialization_error = error_msg
            raise RuntimeError(error_msg)
        
        # Load frameworks
        logger.info("📚 Loading compliance frameworks...")
        fw_data = load_frameworks()
        if not fw_data:
            error_msg = "No compliance frameworks loaded"
            logger.error(error_msg)
            initialization_error = error_msg
            raise RuntimeError(error_msg)
        
        total_sentences = sum(len(fw.get("sentences", [])) for fw in fw_data)
        logger.info(f"Loaded {len(fw_data)} frameworks with {total_sentences} total sentences")
        
        # Build semantic index
        logger.info("🔧 Building semantic search index...")
        result = semantic_engine.build_enhanced_index(fw_data)
        if isinstance(result, tuple):
            framework_index, chunks_metadata = result
            framework_sentences = [chunk.text for chunk in chunks_metadata]
            framework_labels = [chunk.framework_name for chunk in chunks_metadata]
        else:
            framework_index = result
        
        if framework_index is None:
            error_msg = "Semantic index creation failed"
            logger.error(error_msg)
            initialization_error = error_msg
            raise RuntimeError(error_msg)
        
        app_initialized = True
        initialization_error = None
        logger.info("✅ ComplyAI initialized successfully!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize ComplyAI: {e}")
        app_initialized = False
        if not initialization_error:
            initialization_error = str(e)
        yield
    finally:
        logger.info("🔄 ComplyAI shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="Comply",
    description="Compliance document analysis and framework matching API",
    version="2.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(dashboard_router)
app.include_router(report_router)

# Setup CORS and security
setup_cors(app)
apply_owasp_hardening(app)

# Create directories
os.makedirs("data/uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# Serve reports folder
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

def validate_app_health() -> bool:
    """Check if the application is properly initialized"""
    return app_initialized and framework_index is not None

@app.middleware("http")
async def health_check_middleware(request: Request, call_next):
    """Middleware to check app health for core endpoints"""
    critical_endpoints = ["/upload-policy/", "/rebuild-index/"]
    
    if request.url.path in critical_endpoints and not validate_app_health():
        error_detail = initialization_error or "Semantic engine not initialized"
        return JSONResponse(
            status_code=503,
            content={
                "error": f"Service temporarily unavailable - {error_detail}",
                "success": False,
                "retry_after": 60
            }
        )
    
    response = await call_next(request)
    return response

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """User authentication endpoint"""
    try:
        logger.info(f"Login attempt for user: {form_data.username}")

        user = users_db.get(form_data.username)
        
        if not user or not verify_password(form_data.password, user["hashed_password"]):
            logger.warning(f"Failed login attempt for user: {form_data.username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token = create_access_token(data={"sub": user["email"], "role": user["role"]})
        logger.info(f"Successful login for user: {form_data.username}")
        
        return {"access_token": access_token, "token_type": "bearer"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Authentication service temporarily unavailable")

@app.post("/upload-policy/")
async def upload_policy(file: UploadFile = File(...), client_name: str = Form(...)):
    """Upload and analyze policy document"""
    start_time = datetime.now()
    temp_file_path: Optional[str] = None

    try:
        # Add timeout for the upload process
        try:
            await asyncio.wait_for(_process_upload_policy(file, client_name, start_time), timeout=300)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Request timeout - document too large or complex")
    finally:
        # Cleanup temporary file if it exists
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file {temp_file_path}: {e}")

async def _process_upload_policy(file: UploadFile, client_name: str, start_time: datetime):
    temp_file_path: Optional[str] = None
    try:
        # Validate inputs
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
            
        if not client_name.strip():
            raise HTTPException(status_code=400, detail="Client name is required")
        
        client_name = client_name.strip()
        if len(client_name) > 100:
            raise HTTPException(status_code=400, detail="Client name too long (max 100 characters)")
        
        # Validate file format
        allowed_extensions = {".pdf", ".docx"}
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format '{file_ext}'. Please upload PDF or DOCX files."
            )

        # Save uploaded file to temporary location
        temp_fd, temp_file_path = tempfile.mkstemp(suffix=file_ext, prefix="complyai_")
        os.close(temp_fd)
        
        max_file_size = 50 * 1024 * 1024  # 50MB limit
        file_size = 0
        
        with open(temp_file_path, "wb") as buffer:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                
                file_size += len(chunk)
                if file_size > max_file_size:
                    raise HTTPException(status_code=413, detail="File too large (max 50MB)")
                
                buffer.write(chunk)

        logger.info(f"Processing {file_size} byte file: {file.filename} for client: {client_name}")

        # Extract policy content
        policy_sentences = docparser.extract_policy_sentences(temp_file_path)
        if not policy_sentences:
            raise HTTPException(status_code=400, detail="No valid policy content found in the document")

        # Process sentences
        logger.info(f"Processing {len(policy_sentences)} extracted sentences")
        
        cleaned = [s for s in policy_sentences if is_valid_sentence(s)]
        if len(cleaned) < len(policy_sentences) * 0.1:
            cleaned = [s for s in policy_sentences if len(s.strip()) > 30]
        
        try:
            grouped_sentences = group_semantic_sentences(cleaned, threshold=0.7)
        except Exception as e:
            logger.warning(f"Semantic grouping failed: {e}, using cleaned sentences")
            grouped_sentences = cleaned
        
        if not grouped_sentences:
            grouped_sentences = policy_sentences

        logger.info(f"Final processing: {len(policy_sentences)} raw → {len(grouped_sentences)} processed sentences")

        # Generate recommendations
        report_data = recommendation_engine.generate_recommendations(
            grouped_sentences,
            client_name=client_name,
            document_name=file.filename
        )

        if not isinstance(report_data, dict):
            raise HTTPException(status_code=500, detail="Invalid report data structure generated")

        # Generate PDF report
        output_path = pdf_exporter.export_pdf(report_data, client_name)

        # Save JSON report
        safe_client_name = re.sub(r"[^A-Za-z0-9_\-]+", "_", client_name) or "Client"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_filename = f"{safe_client_name}_Compliance_Report_{timestamp}.json"
        json_path = os.path.join("reports", json_filename)
        
        try:
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(report_data, jf, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning(f"Failed to save JSON report: {e}")

        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Successfully processed {file.filename} for {client_name} in {processing_time:.2f}s")

        # Build response
        response_data = {
            "success": True,
            "message": "Policy analysis completed successfully",
            "executive_summary": report_data.get("executive_summary", ""),
            "total_recommendations": len(report_data.get("detailed_report", [])),
            "processing_time_seconds": round(processing_time, 2),
            "report_url": f"/reports/{os.path.basename(output_path)}",
            "file_info": {
                "original_name": file.filename,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2)
            }
        }
        
        if os.path.exists(json_path):
            response_data["json_report_url"] = f"/reports/{json_filename}"
                
        return response_data
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing policy upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing the document")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file {temp_file_path}: {e}")

@app.post("/rebuild-index/")
async def rebuild_index(request: Request, user=Depends(admin_required)):
    """Rebuild the semantic search index (Admin only)"""
    try:
        global framework_index, framework_sentences, framework_labels, initialization_error
        
        logger.info("🔁 Index rebuild requested by admin")
        
        # Reload frameworks
        fw_data = load_frameworks()
        if not fw_data:
            raise HTTPException(status_code=500, detail="No frameworks available for index rebuild")
        
        # Build enhanced index
        result = semantic_engine.build_enhanced_index(fw_data)
        if isinstance(result, tuple):
            framework_index, chunks_metadata = result
            framework_sentences = [chunk.text for chunk in chunks_metadata]
            framework_labels = [chunk.framework_name for chunk in chunks_metadata]
        else:
            framework_index = result
        
        initialization_error = None
        
        vector_count = getattr(framework_index, 'ntotal', 'unknown')
        logger.info(f"✅ Semantic index rebuilt successfully with {vector_count} vectors")
        
        return {
            "success": True,
            "detail": "Semantic index rebuilt successfully",
            "framework_count": len(fw_data),
            "total_vectors": vector_count,
            "rebuild_timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to rebuild index: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rebuild semantic index: {str(e)}")

@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "healthy" if validate_app_health() else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "app_initialized": app_initialized,
        "semantic_engine_ready": framework_index is not None,
        "total_framework_chunks": len(framework_sentences) if framework_sentences else 0,
        "environment": os.getenv("ENV", "development"),
        "version": "2.0.0",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.system()
    }
    
    checks = {
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "reports_directory": os.path.exists("reports"),
        "uploads_directory": os.path.exists("data/uploads"),
    }
    
    if initialization_error:
        health_status["initialization_error"] = initialization_error
    
    health_status["component_checks"] = checks
    health_status["all_checks_passed"] = all(checks.values()) and validate_app_health()
    
    status_code = 200 if health_status["all_checks_passed"] else 503
    
    return JSONResponse(status_code=status_code, content=health_status)

# Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    client_host = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
    logger.warning(f"HTTP {exc.status_code} | {exc.detail} | {request.method} {request.url.path} | From {client_host}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    client_host = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
    logger.warning(f"Validation Error | {request.method} {request.url.path} | {exc} | From {client_host}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid input data",
            "details": exc.errors(),
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    client_host = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
    logger.error(f"Unhandled Exception | {request.method} {request.url.path} | {exc} | From {client_host}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred",
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    if os.getenv("ENV") == "production":
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            workers=int(os.getenv("WORKERS", 1)),
            log_level="warning",
            access_log=False
        )
    else:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )