# api/main.py is the FastAPI application that will serve as the API for uploading and parsing compliance documents and matching them with a cybersecurity framework. It uses the docparser module to extract text from PDF and Word documents, and the semantic_engine module to perform semantic matching using embeddings.


import logging
import sys
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from scripts import docparser, semantic_engine
from models import frameworks
from contextlib import asynccontextmanager
import shutil
import os
from loguru import logger

import scripts.logger_config 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading framework...")
    global index, framework_sentences
    framework_sentences = frameworks.load_framework('data/frameworks/nist_csf_2.0.pdf')
    index, _ = semantic_engine.build_index(framework_sentences)
    logger.success(f"Framework loaded successfully with {len(framework_sentences)} sentences.")
    yield
    logger.info("Application shutdown completed.")

app = FastAPI(lifespan=lifespan)

@app.post("/upload-policy/")
async def upload_policy(request: Request, file: UploadFile = File(...)):
    client_ip = request.client.host
    logger.info(f"Request received from {client_ip} | File: {file.filename}")

    file_path = f"data/uploads/{file.filename}"
    with open(file_path, "wb+") as buffer:
        shutil.copyfileobj(file.file, buffer)
    logger.info(f"File saved: {file_path}")

    if not file.filename.endswith((".pdf", ".docx")):
        logger.warning(f"Rejected file {file.filename}: unsupported file type.")
        raise HTTPException(status_code=400, detail="Unsupported file type. Only PDF and DOCX are allowed.")

    policy_text = docparser.extract_pdf_text(file_path) if file.filename.endswith(".pdf") else docparser.extract_docx_text(file_path)
    policy_sentences = [line.strip() for line in policy_text.split('\n') if line.strip()]
    logger.info(f"Extracted {len(policy_sentences)} sentences from document.")

    D, I = semantic_engine.search(index, policy_sentences)
    logger.success("Semantic search completed.")

    os.remove(file_path)
    logger.info(f"Temporary file {file_path} deleted.")

    return {"matches": [{"policy_sentence": policy_sentences[i], "top_matches": [framework_sentences[j] for j in I[i]]} for i in range(len(policy_sentences))]}


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
