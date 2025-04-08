# scripts/docparser.py
# This script will use the pdfminer library to extract text from PDF files and the python-docx library to extract text from Word documents.


# scripts/docparser.py

from pdfminer.high_level import extract_text
from docx import Document
import os
import json

def extract_pdf_text(pdf_path):
    return extract_text(pdf_path)

def extract_docx_text(docx_path):
    doc = Document(docx_path)
    return '\n'.join([para.text for para in doc.paragraphs])

def parse_framework(input_path: str, framework_name: str, output_path: str):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    if input_path.endswith(".pdf"):
        raw_text = extract_pdf_text(input_path)
    elif input_path.endswith(".docx"):
        raw_text = extract_docx_text(input_path)
    else:
        raise ValueError("Unsupported file format. Use PDF or DOCX.")

    sentences = [line.strip() for line in raw_text.split('\n') if line.strip()]

    framework_json = {
        "name": framework_name,
        "sentences": sentences
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(framework_json, f, indent=2, ensure_ascii=False)

    print(f"Saved: {output_path}")
