"""
Framework loader for cybersecurity compliance frameworks
"""

import os
import json
import logging
from typing import List, Dict

# Setup logging
logger = logging.getLogger(__name__)

def load_frameworks() -> List[Dict]:
    """
    Load frameworks from data/frameworks/*.json
    Each JSON must have: { "name": str, "sentences": [str, ...] }
    """
    frameworks_dir = "data/frameworks"
    data: List[Dict] = []

    if not os.path.exists(frameworks_dir):
        logger.error(f"Frameworks directory '{frameworks_dir}' not found")
        return data

    for fname in os.listdir(frameworks_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(frameworks_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                obj = json.load(f)
            name = obj.get("name", os.path.splitext(fname)[0])
            sentences = obj.get("sentences", [])
            if not isinstance(sentences, list) or not all(isinstance(s, str) for s in sentences):
                logger.warning(f"Invalid sentences in {fname}; skipping.")
                continue
            data.append({"name": name, "sentences": sentences})
            logger.info(f"Loaded framework: {name} ({len(sentences)} sentences)")
        except Exception as e:
            logger.error(f"Failed to load {fname}: {e}")

    logger.info(f"Loaded {len(data)} frameworks")
    return data

def parse_and_save_frameworks():
    """
    Parse raw framework PDFs and save as JSON files
    This function should be called separately, not on import
    """
    from scripts.docparser import parse_framework
    
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
    
    successful_parses = 0
    
    for name, input_path in framework_files.items():
        if not os.path.exists(input_path):
            logger.warning(f"Framework file not found: {input_path}")
            print(f"⚠️ Framework file not found: {input_path}")
            continue
            
        output_path = os.path.join(output_dir, f"{name.replace(' ', '_').lower()}.json")
        
        try:
            parse_framework(input_path, name, output_path)
            successful_parses += 1
            print(f"✅ Parsed {name}")
        except Exception as e:
            logger.error(f"Failed to parse {name}: {e}")
            print(f"❌ Failed to parse {name}: {e}")
    
    print(f"🎯 Successfully parsed {successful_parses}/{len(framework_files)} frameworks")

# Setup logging and suppress PDFMiner warnings
logger = logging.getLogger(__name__)

# Suppress PDFMiner warnings about missing CropBox
pdfminer_logger = logging.getLogger('pdfminer')
pdfminer_logger.setLevel(logging.ERROR)

if __name__ == "__main__":
    # Only run parsing when script is executed directly
    print("🔄 Starting framework parsing...")
    parse_and_save_frameworks()