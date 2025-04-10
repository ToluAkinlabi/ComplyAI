# scripts/rebuild_index.py

import os
from models import frameworks
from scripts import semantic_engine

# Cleanup
for f in [
    "data/framework_index.faiss",
    "data/framework_sentences.json",
    "data/framework_labels.json"
]:
    if os.path.exists(f):
        os.remove(f)
        print(f"🧹 Removed old: {f}")

print("🔄 Rebuilding FAISS index...")

fw_data = frameworks.load_all_frameworks()
index, sentences, labels = semantic_engine.build_multi_framework_index(fw_data)

print(f"✅ Rebuilt index with {len(sentences)} total controls across {len(fw_data)} frameworks.")

