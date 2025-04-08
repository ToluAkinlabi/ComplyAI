# scripts/framework_loader.py

import docparser 
from docparser import parse_framework
import os

# Input file paths
framework_files = {
    "NIST CSF": "data/frameworks_raw/nist_csf_2.0.pdf",
    "ISO 27001": "data/frameworks_raw/iso_27001.pdf",
    "PCI DSS": "data/frameworks_raw/pci_dss_4.0.pdf",
    "SOC 2": "data/frameworks_raw/soc_2.pdf",
    "CIS Controls v8": "data/frameworks_raw/cis_8.pdf"
}

# Output directory
output_dir = "data/frameworks"
os.makedirs(output_dir, exist_ok=True)

for name, input_path in framework_files.items():
    output_path = os.path.join(output_dir, f"{name.replace(' ', '_').lower()}.json")
    parse_framework(input_path, name, output_path)
