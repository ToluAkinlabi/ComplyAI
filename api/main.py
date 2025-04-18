# api/main.py is the FastAPI application that will serve as the API for uploading and parsing compliance documents and matching them with a cybersecurity framework. It uses the docparser module to extract text from PDF and Word documents, and the semantic_engine module to perform semantic matching using embeddings.

#import corsmiddleware
from scripts.cors import setup_cors
from scripts.security_hardening import apply_owasp_hardening
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.staticfiles import StaticFiles

#other imports
import logging
import json
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import shutil
import os
from loguru import logger
from datetime import datetime

# Auth-related imports
from fastapi import Depends
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordRequestForm
from scripts.auth import (
    users_db,
    verify_password,
    create_access_token,
    admin_required,
)

# local imports
from scripts import docparser, semantic_engine, recommendation_engine, report_generator, pdf_exporter
from models import frameworks
from scripts import framework_loader
from scripts.prod_settings import settings
import scripts.logger_config
from contextlib import asynccontextmanager

if os.getenv("ENV") == "production":
    raise HTTPException(status_code=403, detail="Forbidden in production")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global index, framework_sentences, framework_labels
    logger.info("Loading all frameworks...")

    fw_data = frameworks.load_all_frameworks()
    index, framework_sentences, framework_labels = semantic_engine.build_multi_framework_index(fw_data)

    logger.success(f"Loaded and indexed {len(framework_sentences)} total framework sentences across {len(fw_data)} frameworks.")
    yield
    logger.info("API shutdown completed.")

app = FastAPI(lifespan=lifespan)

setup_cors(app)
apply_owasp_hardening(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# Serve reports folder
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# Login
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    print("👉 Username submitted:", form_data.username)
    print("👉 Password submitted:", form_data.password)

    user = users_db.get(form_data.username)
    print("🔍 Retrieved user:", user)

    if not user:
        print("❌ User not found.")
    elif not verify_password(form_data.password, user["hashed_password"]):
        print("❌ Password mismatch.")

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user["email"], "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer"}

# Define your POST endpoint
@app.post("/upload-policy/")
async def upload_policy(file: UploadFile = File(...), client_name: str = Form(...)):
    # Save file temporarily
    file_path = f"data/uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract text
    if file.filename.endswith(".pdf"):
        policy_sentences = docparser.extract_pdf_text(file_path)
    elif file.filename.endswith(".docx"):
        policy_sentences = docparser.extract_docx_text(file_path)
    else:
        return {"error": "Unsupported file format"}

    # Perform semantic search
    embeddings = semantic_engine.model.encode(policy_sentences)
    if len(embeddings.shape) == 1:
        embeddings = embeddings.reshape(1, -1)
    
    k = min(3, index.ntotal)
    D, I = index.search(embeddings, k=k)

    # Generate executive summary & detailed report
    executive_summary, detailed_report = recommendation_engine.generate_recommendations(
        policy_sentences, D, I, framework_sentences, framework_labels
    )

    # Add timestamp
    executive_summary["report_generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Now define report_data
    report_data = {
        "executive_summary": executive_summary,
        "detailed_report": detailed_report
    }

    # Save PDF
    output_path = pdf_exporter.export_pdf(report_data, client_name)

    # Save JSON after report_data is defined
    json_path = f"reports/{client_name.replace(' ', '_')}_Compliance_Report.json"
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(report_data, jf, indent=2, ensure_ascii=False)

    # Clean up uploaded file
    os.remove(file_path)

    return {
        "executive_summary": executive_summary,
        "detailed_report": detailed_report,
        "report_url": f"http://localhost:8000/reports/{os.path.basename(output_path)}"
    }

# List reports
@app.get("/list-reports/")
async def list_reports():
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        return {"reports": []}
    
    files = [
        {"name": f, "modified": os.path.getmtime(os.path.join(reports_dir, f))}
        for f in os.listdir(reports_dir)
        if f.endswith(".pdf")
    ]

    # Sort by latest modified date
    files.sort(key=lambda x: x["modified"], reverse=True)

    return {"reports": files}

# List JSON reports
@app.get("/list-json-reports/")
async def list_json_reports():
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        return {"reports": []}
    
    files = [
        {"name": f, "modified": os.path.getmtime(os.path.join(reports_dir, f))}
        for f in os.listdir(reports_dir)
        if f.endswith(".json")
    ]

    # Sort by latest modified date
    files.sort(key=lambda x: x["modified"], reverse=True)

    return {"reports": files}


# Delete report
@app.delete("/delete-report/{report_name}")
async def delete_report(report_name: str):
    report_path = f"reports/{report_name}"

    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")

    os.remove(report_path)
    return {"detail": "Report deleted successfully"}

#  Rebuild index
@app.post("/rebuild-index/")
async def rebuild_index(request: Request, user=Depends(admin_required)):
    try:
        logger.info(f"🔁 Rebuilding semantic index triggered from UI by {request.client.host}")
        framework_loader.build_all_frameworks_json()  # reprocess frameworks to JSON
        faiss_index, framework_sentences, framework_labels = semantic_engine.build_multi_framework_index_json()
        # update global in-memory index
        globals()["index"] = faiss_index
        globals()["framework_sentences"] = framework_sentences
        globals()["framework_labels"] = framework_labels

        return {"detail": "Semantic index rebuilt successfully."}
    except Exception as e:
        logger.error(f"❌ Failed to rebuild index: {e}")
        raise HTTPException(status_code=500, detail="Failed to rebuild semantic index.")

# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP Error {exc.status_code} | {exc.detail} | From {request.client.host}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation Error | {exc} | From {request.client.host}")
    return JSONResponse(
        status_code=422,
        content={"error": "Invalid input", "details": exc.errors()}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception | {exc} | Path: {request.url.path} | Client: {request.client.host}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred."}
    )
