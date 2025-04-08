# scripts/semantic_matching.py
# This script will use the SentenceTransformer library to embed sentences from a compliance framework and a policy document, and then use the Faiss library to perform semantic matching between the two sets of embeddings. This will help identify relevant framework requirements for a given policy document.

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os
import json

model = SentenceTransformer("all-MiniLM-L6-v2")

def load_all_frameworks(json_dir="../data/frameworks/json"):
    frameworks = []
    for filename in os.listdir(json_dir):
        if filename.endswith(".json"):
            path = os.path.join(json_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                frameworks.append(data)
    return frameworks

def build_multi_framework_index(frameworks_data):
    all_sentences = []
    framework_labels = []

    for fw in frameworks_data:
        all_sentences.extend(fw["sentences"])
        framework_labels.extend([fw["name"]] * len(fw["sentences"]))

    embeddings = model.encode(all_sentences)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    return index, all_sentences, framework_labels
