# models/frameworks.py
# This module handles the loading and processing of cybersecurity frameworks.

from scripts.docparser import extract_pdf_text

def load_framework(file_path):
    text = extract_pdf_text(file_path)
    sentences = [line.strip() for line in text.split('\n') if line.strip()]
    return sentences
