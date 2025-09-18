# Description: This script builds a FAISS index for semantic search using Sentence Transformers. It normalizes the vectors, saves the index and sentences to disk, and provides functions to load the cache. 
# It also checks if the cache exists before building a new index. It uses the Sentence Transformers library to encode sentences into embeddings and FAISS for efficient similarity search and the framework it matched with.

import os
import faiss
import json
import re
import numpy as np
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')

CACHE_DIR = "data"
INDEX_FILE = os.path.join(CACHE_DIR, "framework_index.faiss")
SENTENCES_FILE = os.path.join(CACHE_DIR, "framework_sentences.json")
LABELS_FILE = os.path.join(CACHE_DIR, "framework_labels.json")

def is_valid_sentence(sentence: str) -> bool:
    """Filter out unwanted sentences like dates, urls, emails, numeric junk, etc."""
    if not sentence or len(sentence.strip()) < 15:
        return False
    if re.search(r"\b\d{2,4}[-/]\d{2,4}\b", sentence): 
        return False
    if re.search(r"\bwww\.|\.edu|\.com|\@|\d{5,}", sentence): 
        return False
    if re.fullmatch(r"[A-Za-z]{1,3}(\s?[0-9.]+)+", sentence):  
        return False
    return True

def normalize_vectors(vectors):
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / norms

def save_cache(index, sentences, labels):
    faiss.write_index(index, INDEX_FILE)
    with open(SENTENCES_FILE, "w", encoding="utf-8") as f:
        json.dump(sentences, f, indent=2, ensure_ascii=False)
    with open(LABELS_FILE, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2, ensure_ascii=False)

def load_cache():
    index = faiss.read_index(INDEX_FILE)
    with open(SENTENCES_FILE, "r", encoding="utf-8") as f:
        sentences = json.load(f)
    with open(LABELS_FILE, "r", encoding="utf-8") as f:
        labels = json.load(f)
    return index, sentences, labels

def cache_exists():
    return os.path.exists(INDEX_FILE) and os.path.exists(SENTENCES_FILE) and os.path.exists(LABELS_FILE)

def group_semantic_sentences(sentences, threshold=0.6):
    embeddings = model.encode(sentences, convert_to_tensor=True)
    grouped = []
    used = set()

    for i, emb in enumerate(embeddings):
        if i in used:
            continue
        group = [sentences[i]]
        used.add(i)
        for j in range(i + 1, len(sentences)):
            if j in used:
                continue
            sim = util.cos_sim(emb, embeddings[j]).item()
            if sim >= threshold:
                group.append(sentences[j])
                used.add(j)
        grouped.append(" ".join(group))
    return grouped

def build_multi_framework_index(frameworks_data):
    if cache_exists():
        print("✅ Using cached FAISS index.")
        return load_cache()

    print("🔄 Building FAISS index from frameworks...")
    all_sentences = []
    framework_labels = []

    for fw in frameworks_data:
        all_sentences.extend(fw['sentences'])
        framework_labels.extend([fw['name']] * len(fw['sentences']))

    embeddings = model.encode(all_sentences)
    embeddings = normalize_vectors(np.array(embeddings))

    index = faiss.IndexFlatIP(embeddings.shape[1])  # Cosine similarity
    index.add(embeddings)

    save_cache(index, all_sentences, framework_labels)

    print(f"✅ Indexed {len(all_sentences)} sentences across {len(frameworks_data)} frameworks.")
    return index, all_sentences, framework_labels