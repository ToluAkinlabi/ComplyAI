# scripts/semantic_matching.py
# This script will use the SentenceTransformer library to embed sentences from a compliance framework and a policy document, and then use the Faiss library to perform semantic matching between the two sets of embeddings. This will help identify relevant framework requirements for a given policy document.

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from scripts.docparser import extract_pdf_text, extract_docx_text

model = SentenceTransformer('all-MiniLM-L6-v2')

def build_index(sentences):
    embeddings = model.encode(sentences)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index, embeddings

def search(index, query_sentences, k=3):
    query_embeddings = model.encode(query_sentences)
    D, I = index.search(query_embeddings, k)
    return D, I
