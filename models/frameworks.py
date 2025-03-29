# models/frameworks.py
# This module handles the loading and processing of cybersecurity frameworks.

from scripts.docparser import extract_pdf_text

framework_files = {
    "NIST CSF": "data/frameworks/nist_csf_2.0.pdf",
    "ISO 27001": "data/frameworks/iso_27001.pdf",
    "PCI DSS": "data/frameworks/pci_dss_4.0.pdf",
    "SOC 2": "data/frameworks/soc_2.pdf"
}

def load_all_frameworks():
    frameworks_data = []

    for framework_name, path in framework_files.items():
        text = extract_pdf_text(path)
        sentences = [line.strip() for line in text.split('\n') if line.strip()]
        frameworks_data.append({
            "name": framework_name,
            "sentences": sentences
        })

    return frameworks_data