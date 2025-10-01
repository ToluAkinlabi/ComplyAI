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
from sentence_transformers import SentenceTransformer, util

# Configuration
CONFIG = {
    "model_name": os.getenv("SEMANTIC_MODEL", "all-mpnet-base-v2"),  # Better model
    "window_size": int(os.getenv("CHUNK_WINDOW_SIZE", "3")),
    "stride": int(os.getenv("CHUNK_STRIDE", "1")),
    "grouping_threshold": float(os.getenv("GROUPING_THRESHOLD", "0.7")),
    "cache_version": "v2.0",  # Increment when changing chunking/model
    "max_chunk_length": int(os.getenv("MAX_CHUNK_LENGTH", "512")),
    "min_sentence_length": int(os.getenv("MIN_SENTENCE_LENGTH", "15"))
}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize model
model = SentenceTransformer(CONFIG["model_name"])

# Cache paths
CACHE_DIR = "data"
INDEX_FILE = os.path.join(CACHE_DIR, f"framework_index_{CONFIG['cache_version']}.faiss")
METADATA_FILE = os.path.join(CACHE_DIR, f"framework_metadata_{CONFIG['cache_version']}.json")

@dataclass
class ChunkMetadata:
    """Rich metadata for each chunk"""
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
        self.index = None
        self.chunks_metadata: List[ChunkMetadata] = []
        
    def is_valid_sentence(self, sentence: str) -> bool:
        """Enhanced sentence validation with better filtering"""
        if not sentence or len(sentence.strip()) < CONFIG["min_sentence_length"]:
            return False
            
        # Remove sentences that are mostly dates
        if re.search(r"\b\d{2,4}[-/]\d{2,4}\b", sentence):
            return False
            
        # Remove URLs, emails, and long numeric sequences
        if re.search(r"\b(?:www\.|\.edu|\.com|\@|\d{5,})\b", sentence):
            return False
            
        # Remove sentences that are just codes/numbers
        if re.fullmatch(r"[A-Za-z]{1,3}(\s?[0-9.]+)+", sentence.strip()):
            return False
            
        # Check if sentence has reasonable word ratio (not mostly punctuation)
        words = re.findall(r'\w+', sentence)
        if len(words) < 3:
            return False
            
        # Check stopword ratio to avoid meaningless text
        stopwords = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        word_count = len(words)
        stopword_count = sum(1 for word in words if word.lower() in stopwords)
        if word_count > 0 and stopword_count / word_count > 0.8:
            return False
            
        return True
    
    def preprocess_text(self, text: str) -> str:
        """Enhanced text preprocessing"""
        # Fix broken lines and hyphenation
        text = re.sub(r'-\s*\n\s*', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove extra punctuation
        text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
        return text.strip()
    
    def extract_section_info(self, sentence: str, context: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """Extract section and control ID from sentence and context"""
        control_id = None
        section = None
        
        # Look for control IDs (e.g., AC-1, IA.2.1, etc.)
        control_match = re.search(r'\b([A-Z]{1,3}[-.]?\d+(?:\.\d+)*)\b', sentence)
        if control_match:
            control_id = control_match.group(1)
        
        # Look for section headers in context
        for ctx_sentence in context[-3:]:  # Look at previous sentences
            if re.match(r'^\d+\..*|^[A-Z][A-Z\s]+$', ctx_sentence.strip()):
                section = ctx_sentence.strip()[:50]  # Limit section length
                break
                
        return section, control_id
    
    def hierarchical_chunking(self, sentences: List[str], framework_name: str) -> List[ChunkMetadata]:
        """Create hierarchical chunks with rich metadata"""
        chunks_metadata = []
        
        # First pass: identify sections and controls
        current_section = None
        
        for i, sentence in enumerate(sentences):
            # Check if this looks like a section header
            if re.match(r'^\d+\..*|^[A-Z][A-Z\s]+$', sentence.strip()) and len(sentence) < 100:
                current_section = sentence.strip()
                continue
                
            # Skip invalid sentences
            if not self.is_valid_sentence(sentence):
                continue
                
            # Create overlapping windows
            window_start = max(0, i - CONFIG["window_size"] + 1)
            window_end = min(len(sentences), i + CONFIG["window_size"])
            window_sentences = sentences[window_start:window_end]
            
            # Extract metadata
            section, control_id = self.extract_section_info(sentence, sentences[:i])
            if not section:
                section = current_section
                
            # Create chunk text
            chunk_text = " ".join(window_sentences)
            chunk_text = self.preprocess_text(chunk_text)
            
            # Skip if chunk is too long or short
            if len(chunk_text) > CONFIG["max_chunk_length"] or len(chunk_text) < CONFIG["min_sentence_length"]:
                continue
                
            metadata = ChunkMetadata(
                text=chunk_text,
                framework_name=framework_name,
                control_id=control_id,
                section=section,
                chunk_index=len(chunks_metadata),
                original_sentences=window_sentences,
                embedding_hash=hashlib.md5(chunk_text.encode()).hexdigest()[:8]
            )
            
            chunks_metadata.append(metadata)
            
        return chunks_metadata
    
    def advanced_grouping(self, chunks_metadata: List[ChunkMetadata]) -> List[ChunkMetadata]:
        """Advanced clustering-based grouping to reduce redundancy"""
        if len(chunks_metadata) < 2:
            return chunks_metadata
            
        logger.info(f"Grouping {len(chunks_metadata)} chunks...")
        
        # Create embeddings for clustering
        texts = [chunk.text for chunk in chunks_metadata]
        embeddings = self.model.encode(texts)
        
        # Use Agglomerative Clustering
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - CONFIG["grouping_threshold"],
            linkage='average'
        )
        
        cluster_labels = clustering.fit_predict(embeddings)
        
        # Group chunks by cluster
        clusters = {}
        for i, label in enumerate(cluster_labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(chunks_metadata[i])
        
        # Select representative chunk from each cluster
        grouped_chunks = []
        for cluster_chunks in clusters.values():
            if len(cluster_chunks) == 1:
                grouped_chunks.append(cluster_chunks[0])
            else:
                # Select the chunk with the most comprehensive text
                best_chunk = max(cluster_chunks, key=lambda x: len(x.text))
                # Update metadata to reflect grouping
                best_chunk.original_sentences = [sent for chunk in cluster_chunks for sent in chunk.original_sentences]
                grouped_chunks.append(best_chunk)
        
        logger.info(f"Grouped into {len(grouped_chunks)} representative chunks")
        return grouped_chunks
    
    def build_enhanced_index(self, frameworks_data: List[Dict]) -> Tuple[faiss.Index, List[ChunkMetadata]]:
        """Build enhanced FAISS index with rich metadata"""
        if self.cache_exists():
            logger.info("✅ Using cached enhanced FAISS index.")
            return self.load_cache()
        
        logger.info("🔄 Building enhanced FAISS index with hierarchical chunking...")
        
        all_chunks_metadata = []
        
        for fw in frameworks_data:
            logger.info(f"Processing framework: {fw['name']}")
            
            # Apply hierarchical chunking
            fw_chunks = self.hierarchical_chunking(fw['sentences'], fw['name'])
            
            # Apply advanced grouping
            fw_chunks = self.advanced_grouping(fw_chunks)
            
            all_chunks_metadata.extend(fw_chunks)
        
        # Create embeddings
        texts = [chunk.text for chunk in all_chunks_metadata]
        embeddings = self.model.encode(texts, show_progress_bar=True)
        embeddings = self.normalize_vectors(np.array(embeddings))
        
        # Build FAISS index
        index = faiss.IndexFlatIP(embeddings.shape[1])  # Cosine similarity
        index.add(embeddings)
        
        # Save cache
        self.save_cache(index, all_chunks_metadata)
        
        logger.info(f"✅ Indexed {len(all_chunks_metadata)} enhanced chunks across {len(frameworks_data)} frameworks.")
        
        self.index = index
        self.chunks_metadata = all_chunks_metadata
        
        return index, all_chunks_metadata
    
    def retrieve_with_metadata(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Enhanced retrieval that returns rich metadata for RAG"""
        if self.index is None:
            raise ValueError("Index not built yet. Call build_enhanced_index first.")
        
        # Encode query
        query_embedding = self.model.encode([query])
        query_embedding = self.normalize_vectors(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.chunks_metadata):
                chunk = self.chunks_metadata[idx]
                result = {
                    "text": chunk.text,
                    "framework": chunk.framework_name,
                    "control_id": chunk.control_id,
                    "section": chunk.section,
                    "similarity_score": float(score),
                    "metadata": {
                        "chunk_index": chunk.chunk_index,
                        "embedding_hash": chunk.embedding_hash,
                        "original_sentences_count": len(chunk.original_sentences) if chunk.original_sentences else 0
                    }
                }
                results.append(result)
        
        return results
    
    def prepare_rag_context(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """Prepare enriched context for RAG/LLM consumption"""
        results = self.retrieve_with_metadata(query, top_k)
        
        # Group by framework for better context
        frameworks = {}
        for result in results:
            fw_name = result["framework"]
            if fw_name not in frameworks:
                frameworks[fw_name] = []
            frameworks[fw_name].append(result)
        
        # Prepare structured context
        context = {
            "query": query,
            "total_matches": len(results),
            "frameworks_involved": list(frameworks.keys()),
            "controls": []
        }
        
        for result in results:
            control_info = {
                "text": result["text"],
                "framework": result["framework"],
                "control_id": result["control_id"] or "Unknown",
                "section": result["section"] or "General",
                "confidence": result["similarity_score"],
                "citation": f"{result['framework']} - {result['control_id'] or 'General'}"
            }
            context["controls"].append(control_info)
        
        return context
    
    @staticmethod
    def normalize_vectors(vectors):
        """Normalize vectors for cosine similarity"""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / (norms + 1e-8)  # Add small epsilon to avoid division by zero
    
    def save_cache(self, index: faiss.Index, chunks_metadata: List[ChunkMetadata]):
        """Save enhanced cache with metadata"""
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        faiss.write_index(index, INDEX_FILE)
        
        # Serialize metadata
        metadata_dict = {
            "config": CONFIG,
            "chunks": [
                {
                    "text": chunk.text,
                    "framework_name": chunk.framework_name,
                    "control_id": chunk.control_id,
                    "section": chunk.section,
                    "chunk_index": chunk.chunk_index,
                    "original_sentences": chunk.original_sentences,
                    "embedding_hash": chunk.embedding_hash
                }
                for chunk in chunks_metadata
            ]
        }
        
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved cache: {len(chunks_metadata)} chunks")
    
    def load_cache(self) -> Tuple[faiss.Index, List[ChunkMetadata]]:
        """Load enhanced cache with metadata"""
        index = faiss.read_index(INDEX_FILE)
        
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            metadata_dict = json.load(f)
        
        chunks_metadata = []
        for chunk_data in metadata_dict["chunks"]:
            chunk = ChunkMetadata(
                text=chunk_data["text"],
                framework_name=chunk_data["framework_name"],
                control_id=chunk_data.get("control_id"),
                section=chunk_data.get("section"),
                chunk_index=chunk_data["chunk_index"],
                original_sentences=chunk_data.get("original_sentences", []),
                embedding_hash=chunk_data.get("embedding_hash")
            )
            chunks_metadata.append(chunk)
        
        self.index = index
        self.chunks_metadata = chunks_metadata
        
        logger.info(f"📂 Loaded cache: {len(chunks_metadata)} chunks")
        return index, chunks_metadata
    
    def cache_exists(self) -> bool:
        """Check if enhanced cache exists"""
        return os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE)

# Backward compatibility functions
semantic_engine = EnhancedSemanticEngine()

def build_multi_framework_index(frameworks_data):
    """Backward compatibility wrapper"""
    return semantic_engine.build_enhanced_index(frameworks_data)

def is_valid_sentence(sentence: str) -> bool:
    """Backward compatibility wrapper"""
    return semantic_engine.is_valid_sentence(sentence)

def group_semantic_sentences(sentences, threshold=0.7):
    """Enhanced grouping with clustering"""
    # Create dummy metadata for backward compatibility
    dummy_metadata = [
        ChunkMetadata(text=sent, framework_name="legacy", chunk_index=i)
        for i, sent in enumerate(sentences)
    ]
    
    grouped = semantic_engine.advanced_grouping(dummy_metadata)
    return [chunk.text for chunk in grouped]

# Legacy compatibility - these functions are kept for backward compatibility
def chunk_sentences(sentences, window_size=3, stride=1):
    """Legacy chunking function for backward compatibility"""
    chunks = []
    n = len(sentences)
    for i in range(0, n - window_size + 1, stride):
        chunk = " ".join(sentences[i:i+window_size])
        chunks.append(chunk)
    if n > 0 and (n - window_size) % stride != 0:
        chunk = " ".join(sentences[-window_size:])
        if chunk not in chunks:
            chunks.append(chunk)
    return chunks

def normalize_vectors(vectors):
    """Legacy function for backward compatibility"""
    return EnhancedSemanticEngine.normalize_vectors(vectors)

def save_cache(index, sentences, labels):
    """Legacy save function - will be deprecated"""
    pass

def load_cache():
    """Legacy load function - will be deprecated"""
    pass

def cache_exists():
    """Legacy cache check - will be deprecated"""
    return semantic_engine.cache_exists()