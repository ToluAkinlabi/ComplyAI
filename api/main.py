# api/main.py is the FastAPI application that will serve as the API for uploading and parsing compliance documents and matching them with a cybersecurity framework. It uses the docparser module to extract text from PDF and Word documents, and the semantic_engine module to perform semantic matching using embeddings.

#import corsmiddleware
from scripts.cors import setup_cors
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form

#other imports
import logging
import sys
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import shutil
import os
from loguru import logger
from datetime import datetime

# local imports
from scripts import docparser, semantic_engine, recommendation_engine, report_generator, pdf_exporter
from models import frameworks
import scripts.logger_config
from contextlib import asynccontextmanager


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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

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

    # Clean up uploaded file
    os.remove(file_path)

    # Add timestamp
    executive_summary["report_generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Prepare report data
    report_data = {
        "executive_summary": executive_summary,
        "detailed_report": detailed_report
    }

    # Export PDF
    output_path = pdf_exporter.export_pdf(report_data, client_name)

    # Return result to frontend
    return {
        "executive_summary": executive_summary,
        "detailed_report": detailed_report
    }


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
