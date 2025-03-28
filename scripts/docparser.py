# scripts/document_parser.py
# This script will use the pdfminer library to extract text from PDF files and the python-docx library to extract text from Word documents.

from pdfminer.high_level import extract_text
from docx import Document

def extract_pdf_text(pdf_path):
    return extract_text(pdf_path)

def extract_docx_text(docx_path):
    doc = Document(docx_path)
    return '\n'.join([para.text for para in doc.paragraphs])
