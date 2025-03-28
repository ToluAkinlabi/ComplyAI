# api/main.py is the FastAPI application that will serve as the API for uploading and parsing compliance documents and matching them with a cybersecurity framework. It uses the docparser module to extract text from PDF and Word documents, and the semantic_engine module to perform semantic matching using embeddings.


import logging
import sys
from fastapi import FastAPI, UploadFile, File
from scripts import docparser, semantic_engine
from models import frameworks
from contextlib import asynccontextmanager
import shutil
import os
from scripts.logger_config import get_logger

logger = get_logger("ComplyAI")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


app = FastAPI()

async def lifespan(app: FastAPI):
    global index, framework_sentences
    logger.info("Loading framework from data/frameworks/nist_csf_2.0.pdf ...")
    framework_sentences = frameworks.load_framework('data/frameworks/nist_csf_2.0.pdf')
    index, _ = semantic_engine.build_index(framework_sentences)
    logger.info(f"Framework loaded successfully with {len(framework_sentences)} sentences.")
    yield
    logger.info("API shutdown completed.")

app = FastAPI(lifespan=lifespan)

@app.post("/upload-policy/")
async def upload_policy(file: UploadFile = File(...)):
    logger.info(f"Received file: {file.filename}")

    file_path = f"data/uploads/{file.filename}"
    with open(file_path, "wb+") as buffer:
        shutil.copyfileobj(file.file, buffer)
    logger.info(f"Saved file to {file_path}")

    if file.filename.endswith(".pdf"):
        policy_text = docparser.extract_pdf_text(file_path)
        logger.info("Extracted text from PDF.")
    elif file.filename.endswith(".docx"):
        policy_text = docparser.extract_docx_text(file_path)
        logger.info("Extracted text from DOCX.")
    else:
        logger.warning("Unsupported file type.")
        return {"error": "Unsupported file type"}

    policy_sentences = [line.strip() for line in policy_text.split('\n') if line.strip()]
    logger.info(f"Extracted {len(policy_sentences)} sentences from the policy document.")

    D, I = semantic_engine.search(index, policy_sentences)
    logger.info("Semantic search completed successfully.")

    os.remove(file_path)
    logger.info(f"Temporary file {file_path} removed.")

    return {"matches": [{"policy_sentence": policy_sentences[i], "top_matches": [framework_sentences[j] for j in I[i]]} for i in range(len(policy_sentences))]}
