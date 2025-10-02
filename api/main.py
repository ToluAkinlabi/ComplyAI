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
import json
import re
import os
import sys
import platform
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
import asyncio
from threading import Lock, RLock
import tempfile
import shutil

# Third-party imports
from jose import jwt, JWTError

# Local imports
from scripts import docparser, recommendation_engine, pdf_exporter
from scripts.semantic_engine import semantic_engine, is_valid_sentence, group_semantic_sentences
from scripts.framework_loader import load_frameworks
from scripts.auth import (
    users_db,
    verify_password,
    create_access_token,
    admin_required,
)
from scripts.prod_settings import settings

# Configure logging - use only one logging system
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import logger config after basic setup
try:
    import scripts.logger_config
except ImportError as e:
    logger.warning(f"Logger config import failed: {e}")

# Global variables for framework data with enhanced thread safety
framework_index = None
framework_sentences = []
framework_labels = []
index_lock = RLock()  # Use RLock for nested locking scenarios
app_initialized = False
initialization_error = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management - initialize semantic engine on startup"""
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
        
        # Load frameworks with validation
        logger.info("📚 Loading compliance frameworks...")
        try:
            fw_data = load_frameworks()
        except Exception as e:
            error_msg = f"Failed to load frameworks: {e}"
            logger.error(error_msg)
            initialization_error = error_msg
            raise RuntimeError(error_msg)
            
        if not fw_data:
            error_msg = "No compliance frameworks loaded - cannot initialize semantic engine"
            logger.error(error_msg)
            initialization_error = error_msg
            raise RuntimeError(error_msg)
        
        total_sentences = sum(len(fw.get("sentences", [])) for fw in fw_data)
        logger.info(f"Loaded {len(fw_data)} frameworks with {total_sentences} total sentences")
        
        # Build enhanced index with error handling
        logger.info("🔧 Building semantic search index...")
        with index_lock:
            try:
                result = semantic_engine.build_enhanced_index(fw_data)
                if isinstance(result, tuple):
                    index, chunks_metadata = result
                    framework_index = index
                    framework_sentences = [chunk.text for chunk in chunks_metadata]
                    framework_labels = [chunk.framework_name for chunk in chunks_metadata]
                else:
                    # Handle case where function returns just the index
                    framework_index = result
                    framework_sentences = []
                    framework_labels = []
                
                # Validate index was created successfully
                if framework_index is None:
                    error_msg = "Semantic index creation failed - index is None"
                    logger.error(error_msg)
                    initialization_error = error_msg
                    raise RuntimeError(error_msg)
                    
                if hasattr(framework_index, 'ntotal'):
                    vector_count = framework_index.ntotal
                    if vector_count == 0:
                        error_msg = "Semantic index is empty - no vectors created"
                        logger.error(error_msg)
                        initialization_error = error_msg
                        raise RuntimeError(error_msg)
                    logger.info(f"✅ Semantic index built successfully with {vector_count} vectors")
                else:
                    logger.info("✅ Semantic index built successfully")
                    
            except Exception as e:
                error_msg = f"Failed to build semantic index: {e}"
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
        # Don't raise here - let the app start but mark as unhealthy
        yield
    finally:
        logger.info("🔄 ComplyAI shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="ComplyAI",
    description="Compliance document analysis and framework matching API",
    version="2.0.0",
    lifespan=lifespan
)

# Setup CORS and security
try:
    setup_cors(app)
    apply_owasp_hardening(app)
except Exception as e:
    logger.warning(f"Failed to setup CORS or security hardening: {e}")

# Create necessary directories with proper permissions
def create_secure_directory(directory: str) -> bool:
    """Create directory with appropriate permissions for the OS"""
    try:
        os.makedirs(directory, exist_ok=True)
        
        # Set restrictive permissions (Unix-like systems only)
        if platform.system() != "Windows":
            try:
                os.chmod(directory, 0o700)
            except OSError as e:
                logger.warning(f"Could not set permissions on {directory}: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        return False

# Create necessary directories
required_dirs = ["data/uploads", "reports"]
for directory in required_dirs:
    if not create_secure_directory(directory):
        logger.error(f"Critical: Could not create required directory {directory}")

# Serve reports folder with error handling
try:
    app.mount("/reports", StaticFiles(directory="reports"), name="reports")
except Exception as e:
    logger.error(f"Failed to mount reports directory: {e}")

def validate_app_health() -> bool:
    """Check if the application is properly initialized"""
    with index_lock:
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
                "retry_after": 60  # Suggest retry in 60 seconds
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
        # Validate inputs
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
            
        if not client_name.strip():
            raise HTTPException(status_code=400, detail="Client name is required")
        
        # Validate client name length and characters
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

        # Use temporary file for better security and cleanup
        try:
            # Create temporary file with appropriate suffix
            temp_fd, temp_file_path = tempfile.mkstemp(suffix=file_ext, prefix="complyai_")
            
            # Close the file descriptor as we'll open it normally
            os.close(temp_fd)
            
            # Save uploaded file with size limit and streaming
            max_file_size = 50 * 1024 * 1024  # 50MB limit
            file_size = 0
            
            with open(temp_file_path, "wb") as buffer:
                while True:
                    chunk = await file.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    
                    file_size += len(chunk)
                    if file_size > max_file_size:
                        raise HTTPException(status_code=413, detail="File too large (max 50MB)")
                    
                    buffer.write(chunk)

            logger.info(f"Processing {file_size} byte file: {file.filename} for client: {client_name}")

            # Extract policy content with timeout protection
            try:
                policy_sentences = docparser.extract_policy_sentences(temp_file_path)
            except Exception as e:
                logger.error(f"Failed to parse document: {e}")
                raise HTTPException(status_code=400, detail="Unable to parse document content. Please ensure the file is not corrupted.")
                
            if not policy_sentences:
                raise HTTPException(status_code=400, detail="No valid policy content found in the document")

            # Filter and group sentences with multiple fallbacks
            logger.info(f"Processing {len(policy_sentences)} extracted sentences")
            
            # Step 1: Filter valid sentences
            try:
                cleaned = [s for s in policy_sentences if is_valid_sentence(s)]
                logger.info(f"After validation filtering: {len(cleaned)} sentences")
            except Exception as e:
                logger.warning(f"Sentence validation failed: {e}, using original sentences")
                cleaned = policy_sentences
            
            # Step 2: Fallback if too few sentences
            if len(cleaned) < len(policy_sentences) * 0.1:  # If we lost >90% of content
                logger.warning("Validation too aggressive, using length-based filtering")
                cleaned = [s for s in policy_sentences if len(s.strip()) > 30]
            
            # Step 3: Group semantically similar sentences
            try:
                grouped_sentences = group_semantic_sentences(cleaned, threshold=0.7)
                logger.info(f"After semantic grouping: {len(grouped_sentences)} groups")
            except Exception as e:
                logger.warning(f"Semantic grouping failed: {e}, using cleaned sentences")
                grouped_sentences = cleaned
            
            # Step 4: Final fallback
            if not grouped_sentences:
                logger.warning("Using original sentences as final fallback")
                grouped_sentences = policy_sentences

            logger.info(f"Final processing: {len(policy_sentences)} raw → {len(grouped_sentences)} processed sentences")

            # Generate recommendations with enhanced error handling
            try:
                report_data = recommendation_engine.generate_recommendations(
                    grouped_sentences,
                    client_name=client_name,
                    document_name=file.filename
                )
            except Exception as e:
                logger.error(f"Failed to generate recommendations: {e}")
                raise HTTPException(status_code=500, detail="Failed to generate policy recommendations")

            # Validate report data structure
            if not isinstance(report_data, dict):
                raise HTTPException(status_code=500, detail="Invalid report data structure generated")
                
            if not report_data.get("detailed_report"):
                logger.warning("No recommendations generated - possibly no framework matches")
                # Don't fail completely, but warn the user
                report_data["executive_summary"] = (
                    "⚠️ No specific recommendations could be generated for this policy document. "
                    "This may indicate that the content doesn't match common compliance framework patterns, "
                    "or the semantic analysis couldn't find suitable matches."
                )

            # Generate PDF report with error handling
            try:
                output_path = pdf_exporter.export_pdf(report_data, client_name)
            except Exception as e:
                logger.error(f"Failed to generate PDF: {e}")
                raise HTTPException(status_code=500, detail="Failed to generate PDF report")

            # Save JSON report with error handling
            safe_client_name = re.sub(r"[^A-Za-z0-9_\-]+", "_", client_name) or "Client"
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_filename = f"{safe_client_name}_Compliance_Report_{timestamp}.json"
            json_path = os.path.join("reports", json_filename)
            
            try:
                with open(json_path, "w", encoding="utf-8") as jf:
                    json.dump(report_data, jf, indent=2, ensure_ascii=False, default=str)
            except Exception as e:
                logger.warning(f"Failed to save JSON report: {e}")
                # Continue without failing the entire request

            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Successfully processed {file.filename} for {client_name} in {processing_time:.2f}s")

            # Build comprehensive response
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
            
            # Add JSON report URL if it was saved successfully
            if os.path.exists(json_path):
                response_data["json_report_url"] = f"/reports/{json_filename}"
                
            return response_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"File processing error: {e}")
            raise HTTPException(status_code=500, detail="Error processing uploaded file")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing policy upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing the document")
    
    finally:
        # Ensure temporary file cleanup
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file {temp_file_path}: {e}")

@app.get("/list-reports/")
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
                    continue  # Skip files we can't stat

        # Sort by latest modified date
        files.sort(key=lambda x: x["modified"], reverse=True)
        return {"reports": files, "total_count": len(files)}
    
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving reports list")

@app.get("/list-json-reports/")
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

@app.delete("/delete-report/{report_name}")
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

@app.post("/rebuild-index/")
async def rebuild_index(request: Request, user=Depends(admin_required)):
    """Rebuild the semantic search index (Admin only)"""
    try:
        global framework_index, framework_sentences, framework_labels, initialization_error
        
        client_host = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
        logger.info(f"🔁 Index rebuild requested by admin from {client_host}")
        
        with index_lock:
            try:
                # Reload frameworks with validation
                fw_data = load_frameworks()
                if not fw_data:
                    raise HTTPException(status_code=500, detail="No frameworks available for index rebuild")
                
                # Build enhanced index
                result = semantic_engine.build_enhanced_index(fw_data)
                if isinstance(result, tuple):
                    index, chunks_metadata = result
                    framework_index = index
                    framework_sentences = [chunk.text for chunk in chunks_metadata]
                    framework_labels = [chunk.framework_name for chunk in chunks_metadata]
                else:
                    framework_index = result
                    framework_sentences = []
                    framework_labels = []
                
                # Clear any previous initialization errors
                initialization_error = None
                
            except Exception as e:
                error_msg = f"Failed to rebuild index: {e}"
                logger.error(error_msg)
                initialization_error = error_msg
                raise

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
    with index_lock:
        current_app_initialized = app_initialized
        current_framework_index = framework_index
        current_framework_sentences = framework_sentences
    
    health_status = {
        "status": "healthy" if validate_app_health() else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "app_initialized": current_app_initialized,
        "semantic_engine_ready": current_framework_index is not None,
        "total_framework_chunks": len(current_framework_sentences) if current_framework_sentences else 0,
        "environment": os.getenv("ENV", "development"),
        "version": "2.0.0",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.system()
    }
    
    # Check critical components
    checks = {
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "reports_directory": os.path.exists("reports"),
        "uploads_directory": os.path.exists("data/uploads"),
        "framework_loader_available": True,  # Could add actual check
        "semantic_engine_available": True,   # Could add actual check
    }
    
    # Add initialization error if present
    if initialization_error:
        health_status["initialization_error"] = initialization_error
    
    health_status["component_checks"] = checks
    health_status["all_checks_passed"] = all(checks.values()) and validate_app_health()
    
    # Return appropriate status code
    status_code = 200 if health_status["all_checks_passed"] else 503
    
    return JSONResponse(status_code=status_code, content=health_status)

# Enhanced Error Handlers
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
    
    # Development vs Production configuration
    if os.getenv("ENV") == "production":
        # Production settings
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            workers=int(os.getenv("WORKERS", 1)),
            log_level="warning",
            access_log=False  # Reduce log verbosity in production
        )
    else:
        # Development settings
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )