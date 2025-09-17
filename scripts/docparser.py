# scripts/docparser.py
# This script will use the pdfminer library to extract text from PDF files and the python-docx library to extract text from Word documents.


# scripts/docparser.py

from pdfminer.high_level import extract_text
from docx import Document
import os
import json
import re
from nltk.tokenize import sent_tokenize

def extract_pdf_text(pdf_path):
    return extract_text(pdf_path)


def extract_docx_text(docx_path):
    doc = Document(docx_path)
    return '\n'.join([para.text for para in doc.paragraphs])


def is_valid_policy_line(line):
    if len(line) < 8:
        return False
    if re.search(r'\b(?:https?://|www\.)\S+', line):  # URLs
        return False
    if re.search(r'@\w+\.\w+', line):  # Emails
        return False
    if re.match(r'^[\d\s\.\-\/]+$', line):  # Pure numbers, dates, versions
        return False
    if len(line.split()) <= 3:  # Very short phrases
        return False
    return True


def is_valid_policy_sentence(line: str) -> bool:
    if len(line.strip()) < 5:
        return False
    if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", line):  # date format
        return False
    if re.match(r"^(https?://)?[\w.-]+\.\w{2,}$", line):  # simple URL/email pattern
        return False
    if line.strip().lower() in {"version", "date", "email", "contact", "phone"}:
        return False
    return True


def extract_policy_sentences(filepath):
    if filepath.endswith(".pdf"):
        raw = extract_pdf_text(filepath)
    elif filepath.endswith(".docx"):
        raw = extract_docx_text(filepath)
    else:
        raise ValueError("Unsupported file format.")
    
    paragraphs = [p.strip() for p in raw.split("\n\n") if len(p.strip()) > 50 and len(p.strip()) < 1000]
    return paragraphs


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
