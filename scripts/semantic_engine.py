"""
Enhanced Semantic Engine with configurable models, hierarchical chunking,
metadata enrichment, and improved RAG integration.
"""
import os
import faiss
import json
import re
import logging
import hashlib
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from sklearn.cluster import AgglomerativeClustering
import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder

# Configuration
CONFIG = {
    "model_name": os.getenv("SEMANTIC_MODEL", "all-mpnet-base-v2"),
    "enable_reranker": os.getenv("ENABLE_RERANKER", "false").lower() == "true",
    "reranker_model_name": os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
    "reranker_candidate_multiplier": int(os.getenv("RERANKER_CANDIDATE_MULTIPLIER", "4")),
    "reranker_top_n": int(os.getenv("RERANKER_TOP_N", "20")),
    "window_size": int(os.getenv("CHUNK_WINDOW_SIZE", "3")),
    "stride": int(os.getenv("CHUNK_STRIDE", "1")),
    "grouping_threshold": float(os.getenv("GROUPING_THRESHOLD", "0.7")),
    "cache_version": "v2.0",
    "max_chunk_length": int(os.getenv("MAX_CHUNK_LENGTH", "512")),
    "min_sentence_length": int(os.getenv("MIN_SENTENCE_LENGTH", "12")),  # relaxed from 15
}

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model
model = SentenceTransformer(CONFIG["model_name"])

# Cache paths
CACHE_DIR = "data"
INDEX_FILE = os.path.join(CACHE_DIR, f"framework_index_{CONFIG['cache_version']}.faiss")
METADATA_FILE = os.path.join(CACHE_DIR, f"framework_metadata_{CONFIG['cache_version']}.json")

@dataclass
class ChunkMetadata:
    text: str
    framework_name: str
    control_id: Optional[str] = None
    section: Optional[str] = None
    chunk_index: int = 0
    original_sentences: List[str] = None
    embedding_hash: Optional[str] = None

class EnhancedSemanticEngine:
    def __init__(self):
        self.model = model
        self.reranker = None
        self.index = None
        self.chunks_metadata: List[ChunkMetadata] = []

        if CONFIG["enable_reranker"]:
            try:
                self.reranker = CrossEncoder(CONFIG["reranker_model_name"])
                logger.info(f"✅ Reranker enabled with model {CONFIG['reranker_model_name']}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize reranker: {e}")
                self.reranker = None

    def is_valid_sentence(self, sentence: str) -> bool:
        if not sentence or len(sentence.strip()) < CONFIG["min_sentence_length"]:
            return False
        if re.search(r"\b\d{2,4}[-/]\d{2,4}\b", sentence):  # dates like 11-2014
            return False
        if re.search(r"\b(?:www\.|\.edu|\.com|\@|\d{5,})\b", sentence):  # urls/emails/long digits
            return False
        if re.fullmatch(r"[A-Za-z]{1,3}(\s?[0-9.]+)+", sentence.strip()):  # code fragments
            return False
        words = re.findall(r'\w+', sentence)
        if len(words) < 3:
            return False
        return True

    def preprocess_text(self, text: str) -> str:
        text = re.sub(r'-\s*\n\s*', '', text)         # de-hyphenate line-breaks
        text = re.sub(r'\s+', ' ', text)              # normalize whitespace
        text = re.sub(r'[^\w\s.,;:!?()-]', '', text)  # strip odd punctuation
        return text.strip()

    def extract_section_info(self, sentence: str, context: List[str]) -> Tuple[Optional[str], Optional[str]]:
        control_id = None
        section = None
        m = re.search(r'\b([A-Z]{1,3}[-.]?\d+(?:\.\d+)*)\b', sentence)
        if m:
            control_id = m.group(1)
        for ctx in context[-3:]:
            if re.match(r'^\d+\..*|^[A-Z][A-Z\s]+$', ctx.strip()):
                section = ctx.strip()[:50]
                break
        return section, control_id

    def hierarchical_chunking(self, sentences: List[str], framework_name: str) -> List[ChunkMetadata]:
        chunks_metadata = []
        current_section = None
        for i, sentence in enumerate(sentences):
            if re.match(r'^\d+\..*|^[A-Z][A-Z\s]+$', sentence.strip()) and len(sentence) < 100:
                current_section = sentence.strip()
                continue
            if not self.is_valid_sentence(sentence):
                continue

            window_start = max(0, i - CONFIG["window_size"] + 1)
            window_end = min(len(sentences), i + CONFIG["window_size"])
            window_sentences = sentences[window_start:window_end]
            section, control_id = self.extract_section_info(sentence, sentences[:i])
            if not section:
                section = current_section

            chunk_text = " ".join(window_sentences)
            chunk_text = self.preprocess_text(chunk_text)
            if len(chunk_text) > CONFIG["max_chunk_length"] or len(chunk_text) < CONFIG["min_sentence_length"]:
                continue

            metadata = ChunkMetadata(
                text=chunk_text,
                framework_name=framework_name,
                control_id=control_id,
                section=section,
                chunk_index=len(chunks_metadata),
                original_sentences=window_sentences,
                embedding_hash=hashlib.md5(chunk_text.encode()).hexdigest()[:8],
            )
            chunks_metadata.append(metadata)
        return chunks_metadata

    def advanced_grouping(self, chunks_metadata: List[ChunkMetadata], threshold: Optional[float] = None) -> List[ChunkMetadata]:
        """Cluster chunks to reduce redundancy. Threshold is cosine-sim similarity."""
        if len(chunks_metadata) < 2:
            return chunks_metadata

        thr = float(threshold) if threshold is not None else float(CONFIG["grouping_threshold"])
        logger.info(f"Grouping {len(chunks_metadata)} chunks with threshold={thr}...")

        texts = [c.text for c in chunks_metadata]
        embs = self.model.encode(texts)
        # AgglomerativeClustering with 'average' linkage approximates cosine threshold via 1 - thr
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - thr,
            linkage='average'
        )
        labels = clustering.fit_predict(embs)

        clusters: Dict[int, List[ChunkMetadata]] = {}
        for i, label in enumerate(labels):
            clusters.setdefault(label, []).append(chunks_metadata[i])

        grouped: List[ChunkMetadata] = []
        for members in clusters.values():
            if len(members) == 1:
                grouped.append(members[0])
            else:
                best = max(members, key=lambda x: len(x.text))
                best.original_sentences = [s for m in members for s in (m.original_sentences or [])]
                grouped.append(best)

        logger.info(f"Grouped into {len(grouped)} representative chunks")
        return grouped

    def build_enhanced_index(self, frameworks_data: List[Dict]) -> Tuple[faiss.Index, List[ChunkMetadata]]:
        if self.cache_exists():
            logger.info("✅ Using cached enhanced FAISS index.")
            return self.load_cache()

        logger.info("🔄 Building enhanced FAISS index with hierarchical chunking...")
        all_chunks: List[ChunkMetadata] = []
        for fw in frameworks_data:
            logger.info(f"Processing framework: {fw['name']}")
            fw_chunks = self.hierarchical_chunking(fw['sentences'], fw['name'])
            fw_chunks = self.advanced_grouping(fw_chunks)  # uses config threshold
            all_chunks.extend(fw_chunks)

        if not all_chunks:
            raise RuntimeError("No framework chunks generated. Check your data/frameworks/*.json files.")

        texts = [c.text for c in all_chunks]
        embs = self.model.encode(texts, show_progress_bar=True)
        embs = self.normalize_vectors(np.array(embs))

        index = faiss.IndexFlatIP(embs.shape[1])
        index.add(embs)

        self.save_cache(index, all_chunks)
        logger.info(f"✅ Indexed {len(all_chunks)} enhanced chunks across {len(frameworks_data)} frameworks.")

        self.index = index
        self.chunks_metadata = all_chunks
        return index, all_chunks

    def retrieve_with_metadata(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.index is None:
            raise ValueError("Index not built yet. Call build_enhanced_index first.")

        q = self.model.encode([query])
        q = self.normalize_vectors(q)
        candidate_k = top_k
        if self.reranker is not None:
            candidate_k = max(top_k * CONFIG["reranker_candidate_multiplier"], CONFIG["reranker_top_n"], top_k)
        candidate_k = min(candidate_k, len(self.chunks_metadata))

        scores, indices = self.index.search(q, candidate_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(self.chunks_metadata):
                c = self.chunks_metadata[idx]
                results.append({
                    "text": c.text,
                    "framework": c.framework_name,
                    "control_id": c.control_id,
                    "section": c.section,
                    "similarity_score": float(score),
                    "metadata": {
                        "chunk_index": c.chunk_index,
                        "embedding_hash": c.embedding_hash,
                        "original_sentences_count": len(c.original_sentences) if c.original_sentences else 0,
                        "reranker_score": None,
                    }
                })

        if self.reranker is not None and results:
            try:
                pairs = [[query, item["text"]] for item in results]
                rerank_scores = self.reranker.predict(pairs)
                for item, rerank_score in zip(results, rerank_scores):
                    item["metadata"]["reranker_score"] = float(rerank_score)

                results.sort(key=lambda item: item["metadata"].get("reranker_score", -9999.0), reverse=True)
            except Exception as e:
                logger.warning(f"⚠️ Reranking failed, using vector ranking only: {e}")

        return results[:top_k]

    @staticmethod
    def normalize_vectors(vectors):
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / (norms + 1e-8)

    def save_cache(self, index: faiss.Index, chunks: List[ChunkMetadata]):
        os.makedirs(CACHE_DIR, exist_ok=True)
        faiss.write_index(index, INDEX_FILE)
        payload = {
            "config": CONFIG,
            "chunks": [{
                "text": c.text,
                "framework_name": c.framework_name,
                "control_id": c.control_id,
                "section": c.section,
                "chunk_index": c.chunk_index,
                "original_sentences": c.original_sentences,
                "embedding_hash": c.embedding_hash
            } for c in chunks]
        }
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved cache: {len(chunks)} chunks")

    def load_cache(self) -> Tuple[faiss.Index, List[ChunkMetadata]]:
        index = faiss.read_index(INDEX_FILE)
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)

        chunks: List[ChunkMetadata] = []
        for cd in payload["chunks"]:
            chunks.append(ChunkMetadata(
                text=cd["text"],
                framework_name=cd["framework_name"],
                control_id=cd.get("control_id"),
                section=cd.get("section"),
                chunk_index=cd["chunk_index"],
                original_sentences=cd.get("original_sentences", []),
                embedding_hash=cd.get("embedding_hash")
            ))
        self.index = index
        self.chunks_metadata = chunks
        logger.info(f"📂 Loaded cache: {len(chunks)} chunks")
        return index, chunks

    def cache_exists(self) -> bool:
        return os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE)

# Singleton
semantic_engine = EnhancedSemanticEngine()

# Backward compatibility wrappers
def build_multi_framework_index(frameworks_data):
    return semantic_engine.build_enhanced_index(frameworks_data)

def is_valid_sentence(sentence: str) -> bool:
    return semantic_engine.is_valid_sentence(sentence)

def group_semantic_sentences(sentences: List[str], threshold: float = 0.7) -> List[str]:
    # Build temporary metadata, then cluster with the provided threshold
    temp = [ChunkMetadata(text=s, framework_name="doc", chunk_index=i) for i, s in enumerate(sentences)]
    grouped = semantic_engine.advanced_grouping(temp, threshold=threshold)
    return [g.text for g in grouped]

# Legacy helpers kept for compatibility (unused in new path)
def chunk_sentences(sentences, window_size=3, stride=1):
    chunks = []
    n = len(sentences)
    for i in range(0, n - window_size + 1, stride):
        chunks.append(" ".join(sentences[i:i+window_size]))
    if n > 0 and (n - window_size) % stride != 0:
        chunk = " ".join(sentences[-window_size:])
        if chunk not in chunks:
            chunks.append(chunk)
    return chunks
