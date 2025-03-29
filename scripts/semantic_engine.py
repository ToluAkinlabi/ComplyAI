# scripts/semantic_matching.py
# This script will use the SentenceTransformer library to embed sentences from a compliance framework and a policy document, and then use the Faiss library to perform semantic matching between the two sets of embeddings. This will help identify relevant framework requirements for a given policy document.

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

def build_multi_framework_index(frameworks_data):
    all_sentences = []
    framework_labels = []

    for fw in frameworks_data:
        all_sentences.extend(fw['sentences'])
        framework_labels.extend([fw['name']] * len(fw['sentences']))

    embeddings = model.encode(all_sentences)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    return index, all_sentences, framework_labels