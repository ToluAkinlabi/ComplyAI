import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
import time
import hashlib
from functools import lru_cache

from scripts.semantic_engine import semantic_engine
from scripts.framework_loader import load_frameworks

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Enhanced configuration with performance optimizations
CONFIG = {
    "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "max_completion_tokens": int(os.getenv("MAX_COMPLETION_TOKENS", "200")),
    "temperature_env": os.getenv("OPENAI_TEMPERATURE", "0.6"),
    "aligned_threshold": float(os.getenv("ALIGNED_THRESHOLD", "0.7")),
    "weak_threshold": float(os.getenv("WEAK_THRESHOLD", "0.4")),
    "max_suggestions": int(os.getenv("MAX_SUGGESTIONS", "3")),
    # Performance optimization settings
    "batch_size": 10,
    "suggestion_batch_size": 5,
    "max_concurrent_workers": 3,
    "cache_similarity": True,
}

# Parse temperature once
try:
    CONFIG["temperature"] = float(CONFIG["temperature_env"])
except Exception:
    CONFIG["temperature"] = 0.6

# Caching system for performance optimization
_similarity_cache = {}
_cache_max_size = 1000

@lru_cache(maxsize=500)
def _get_sentence_hash(sentence: str) -> str:
    """Generate hash for sentence caching"""
    return hashlib.md5(sentence.lower().encode()).hexdigest()[:16]

def _get_cached_similarity(sentence_hash: str):
    """Get cached similarity results"""
    return _similarity_cache.get(sentence_hash)

def _cache_similarity(sentence_hash: str, results):
    """Cache similarity results with size limit"""
    if len(_similarity_cache) >= _cache_max_size:
        # Remove oldest entries
        oldest_keys = list(_similarity_cache.keys())[:100]
        for key in oldest_keys:
            del _similarity_cache[key]
    _similarity_cache[sentence_hash] = results

def _extract_control_id_optimized(best: Dict, index: int) -> str:
    """Optimized control ID extraction with fallbacks"""
    control_id = (
        best.get("control_id") or 
        best.get("id") or 
        best.get("control_number") or 
        best.get("requirement_id") or
        f"{best.get('framework', 'UNK')}-{index+1:03d}"
    )
    
    if not control_id or control_id == "Unknown":
        control_id = f"{best.get('framework', 'UNKNOWN')}-REQ-{index+1:03d}"
    
    return control_id

@lru_cache(maxsize=100)
def _extract_section_optimized(framework: str, section: str, category: str, domain: str) -> str:
    """Cached section extraction"""
    return section or category or domain or "General"

def _optimize_memory_usage():
    """Clean up memory periodically"""
    import gc
    
    # Clear caches if they get too large
    if len(_similarity_cache) > 800:
        _similarity_cache.clear()
        logger.info("🧹 Cleared similarity cache")
    
    # Force garbage collection
    gc.collect()

# OpenAI client setup
OPENAI_NEW_API = False
client = None
OPENAI_API_READY = False

try:
    import openai

    if hasattr(openai, "OpenAI"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        client = openai.OpenAI(api_key=api_key)
        OPENAI_NEW_API = True
        OPENAI_API_READY = True
        logger.info(f"✅ OpenAI new API initialized. Model={CONFIG['openai_model']}")
    else:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        OPENAI_NEW_API = False
        OPENAI_API_READY = True
        logger.info(f"✅ OpenAI legacy API initialized. Model={CONFIG['openai_model']}")
except Exception as e:
    logger.error(f"❌ Failed to initialize OpenAI client: {e}")
    OPENAI_API_READY = False

def _call_llm_with_retry(prompt: str) -> str:
    """Calls OpenAI chat API with robust fallbacks for parameter compatibility"""
    if not OPENAI_API_READY:
        logger.warning("⚠️ OpenAI API not configured; returning stub suggestion.")
        return "LLM unavailable. Please review this control manually."

    messages = [{"role": "user", "content": prompt}]
    temp = CONFIG["temperature"]
    max_tok = CONFIG["max_completion_tokens"]

    def do_call_new(include_temp: bool, use_max_tokens: bool):
        params = {
            "model": CONFIG["openai_model"],
            "messages": messages,
        }
        if use_max_tokens:
            params["max_tokens"] = max_tok
        
        if include_temp and temp is not None:
            params["temperature"] = float(temp)

        return client.chat.completions.create(**params)

    def do_call_legacy(include_temp: bool):
        params = {
            "model": CONFIG["openai_model"],
            "messages": messages,
            "max_tokens": max_tok,
        }
        if include_temp and temp is not None:
            params["temperature"] = float(temp)
        return openai.ChatCompletion.create(**params)

    # Strategy 1: Full parameters
    try:
        if OPENAI_NEW_API:
            return do_call_new(include_temp=True, use_max_tokens=True).choices[0].message.content.strip()
        else:
            return do_call_legacy(include_temp=True).choices[0].message.content.strip()
    except Exception as e1:
        logger.info(f"🔄 Retry 1 - removing temperature: {str(e1)[:100]}")

    # Strategy 2: Remove temperature
    try:
        if OPENAI_NEW_API:
            return do_call_new(include_temp=False, use_max_tokens=True).choices[0].message.content.strip()
        else:
            return do_call_legacy(include_temp=False).choices[0].message.content.strip()
    except Exception as e2:
        logger.info(f"🔄 Retry 2 - removing token limit: {str(e2)[:100]}")

    # Strategy 3: Remove token limit
    try:
        if OPENAI_NEW_API:
            return do_call_new(include_temp=False, use_max_tokens=False).choices[0].message.content.strip()
        else:
            return openai.ChatCompletion.create(
                model=CONFIG["openai_model"], 
                messages=messages
            ).choices[0].message.content.strip()
    except Exception as e3:
        logger.error(f"❌ All retry attempts failed: {e3}")
        return "Unable to generate suggestion due to model parameter restrictions."

def suggest_improvement(sentence: str, closest_controls_with_metadata: List[Dict]) -> str:
    """Generate policy improvement suggestions using OpenAI with concise output"""
    try:
        if not closest_controls_with_metadata:
            return "No relevant controls found."

        context_parts, citations = [], []
        for i, control_data in enumerate(closest_controls_with_metadata[:2], 1):
            if not isinstance(control_data, dict):
                continue
            
            control_text = control_data.get("text", "Unknown")[:200]
            framework = control_data.get("framework", "Unknown")
            control_id = control_data.get("control_id", "Unknown")
            confidence = float(control_data.get("similarity_score", 0.0) or 0.0)

            context_parts.append(f"[{framework}-{control_id}] {control_text}")
            citations.append(f"{framework}-{control_id}")

        if not context_parts:
            return "Insufficient framework guidance."

        prompt = (
            "As a compliance expert, provide a concise improved policy statement.\n\n"
            f"Current Policy: {sentence[:300]}\n\n"
            f"Reference Controls:\n" + "\n".join(context_parts) + 
            f"\n\nProvide ONE improved policy sentence (max 2 lines) that addresses the gap. "
            f"Cite: {', '.join(citations)}"
        )

        return _call_llm_with_retry(prompt)
    except Exception as e:
        logger.error(f"❌ Error preparing suggestion prompt: {e}")
        return "Unable to generate suggestion."

def suggest_improvement_batch(sentences_and_controls: List[Tuple[str, List[Dict]]]) -> List[str]:
    """Generate multiple policy improvement suggestions in parallel"""
    if not sentences_and_controls:
        return []
    
    if len(sentences_and_controls) <= 3:
        return _batch_suggest_combined(sentences_and_controls)
    
    return _batch_suggest_parallel(sentences_and_controls)

def _batch_suggest_combined(sentences_and_controls: List[Tuple[str, List[Dict]]]) -> List[str]:
    """Combine multiple suggestions into one API call"""
    try:
        batch_prompt = "You are a compliance expert. Provide concise policy improvements for each:\n\n"
        
        for i, (sentence, controls) in enumerate(sentences_and_controls, 1):
            if controls and isinstance(controls[0], dict):
                control = controls[0]
                framework = control.get("framework", "Unknown")
                control_id = control.get("control_id", "Unknown")
                control_text = control.get("text", "Unknown")[:150]
                
                batch_prompt += (
                    f"POLICY {i}: {sentence[:200]}\n"
                    f"Reference: [{framework}-{control_id}] {control_text}\n"
                    f"Improvement {i}: [Your improved policy here]\n\n"
                )
        
        batch_prompt += "Provide ONLY the improvements, numbered 1-N, max 2 lines each."
        
        response = _call_llm_with_retry(batch_prompt)
        
        # Parse the response
        improvements = []
        lines = response.split('\n')
        current_improvement = ""
        
        for line in lines:
            if line.strip() and (line.startswith(('1.', '2.', '3.', 'Improvement')) or 
                               any(f'{i}:' in line for i in range(1, 10))):
                if current_improvement:
                    improvements.append(current_improvement.strip())
                current_improvement = line.split(':', 1)[-1].strip() if ':' in line else line.strip()
            elif current_improvement and line.strip():
                current_improvement += " " + line.strip()
        
        if current_improvement:
            improvements.append(current_improvement.strip())
        
        while len(improvements) < len(sentences_and_controls):
            improvements.append("Unable to generate specific improvement.")
        
        return improvements[:len(sentences_and_controls)]
    
    except Exception as e:
        logger.error(f"❌ Error in batch suggestion: {e}")
        return ["Unable to generate suggestion."] * len(sentences_and_controls)

def _batch_suggest_parallel(sentences_and_controls: List[Tuple[str, List[Dict]]]) -> List[str]:
    """Process suggestions in parallel with limited workers"""
    def process_single(sentence_and_controls):
        sentence, controls = sentence_and_controls
        return suggest_improvement(sentence, controls)
    
    try:
        with ThreadPoolExecutor(max_workers=CONFIG["max_concurrent_workers"]) as executor:
            futures = [executor.submit(process_single, item) for item in sentences_and_controls]
            results = []
            
            for future in futures:
                try:
                    result = future.result(timeout=15)
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ Error in parallel suggestion: {e}")
                    results.append("Unable to generate suggestion.")
            
            return results
    except Exception as e:
        logger.error(f"❌ Error in parallel processing: {e}")
        return ["Unable to generate suggestion."] * len(sentences_and_controls)

def _bootstrap_index_if_needed() -> bool:
    """Ensure the FAISS index is available with validation"""
    if getattr(semantic_engine, "index", None) is not None:
        try:
            if hasattr(semantic_engine.index, 'ntotal') and semantic_engine.index.ntotal > 0:
                logger.info(f"✅ Semantic index already available with {semantic_engine.index.ntotal} vectors")
                return True
        except:
            pass
    
    try:
        logger.info("🔄 Bootstrapping semantic index...")
        fw_data = load_frameworks()
        if not fw_data:
            logger.error("❌ No frameworks loaded; cannot build index.")
            return False
        
        total_sentences = sum(len(fw.get("sentences", [])) for fw in fw_data)
        if total_sentences == 0:
            logger.error("❌ No sentences found in framework data.")
            return False
            
        logger.info(f"📚 Loading {len(fw_data)} frameworks with {total_sentences} total sentences")
        semantic_engine.build_enhanced_index(fw_data)
        
        if hasattr(semantic_engine.index, 'ntotal') and semantic_engine.index.ntotal > 0:
            logger.info(f"✅ Semantic index built successfully with {semantic_engine.index.ntotal} vectors")
            return True
        else:
            logger.error("❌ Index was created but appears to be empty")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to bootstrap index: {e}")
        return False

def generate_recommendations(policy_sentences: List[str], client_name: str = "Client", document_name: str = "Document") -> Dict[str, Any]:
    """Generate complete report data structure for PDF export with optimized processing"""
    start_time = datetime.now()
    
    if not _bootstrap_index_if_needed():
        error_report = {
            "executive_summary": "❌ Failed to initialize semantic engine. No recommendations generated.",
            "detailed_report": [],
            "metadata": {
                "client_name": client_name,
                "document_name": document_name,
                "total_sentences": len(policy_sentences),
                "processed_sentences": 0,
                "total_recommendations": 0,
                "report_generated_at": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "processing_time_seconds": 0.0,
                "model_used": CONFIG["openai_model"],
                "error": "Semantic engine initialization failed"
            }
        }
        logger.error("❌ Returning error report due to initialization failure")
        return error_report

    recommendations: List[Dict[str, Any]] = []
    weak_sentences = []
    
    logger.info(f"🔍 Processing {len(policy_sentences)} policy sentences with caching")

    # Main processing loop with caching optimization
    for i, sentence in enumerate(policy_sentences):
        try:
            # Add caching for similarity calculations
            sentence_hash = _get_sentence_hash(sentence)
            cached_result = _get_cached_similarity(sentence_hash)
            
            if cached_result and CONFIG.get("cache_similarity", True):
                results_with_metadata = cached_result
                logger.debug(f"📋 Using cached similarity for sentence {i+1}")
            else:
                results_with_metadata = semantic_engine.retrieve_with_metadata(
                    sentence, top_k=CONFIG["max_suggestions"]
                )
                # Cache the result
                if CONFIG.get("cache_similarity", True):
                    _cache_similarity(sentence_hash, results_with_metadata)
            
            if not isinstance(results_with_metadata, list) or not results_with_metadata:
                logger.warning(f"⚠️ No results for sentence {i+1}")
                continue

            best = results_with_metadata[0]
            if not isinstance(best, dict):
                logger.warning(f"⚠️ Invalid result format for sentence {i+1}")
                continue

            sim = float(best.get("similarity_score", 0.0) or 0.0)
            
            # Optimized extraction functions
            control_id = _extract_control_id_optimized(best, i)
            section = _extract_section_optimized(
                best.get("framework", ""),
                best.get("section", ""),
                best.get("category", ""),
                best.get("domain", "")
            )
            
            if sim >= CONFIG["aligned_threshold"]:
                status, priority = "Aligned", "Low"
            elif sim >= CONFIG["weak_threshold"]:
                status, priority = "Weak", "Medium"
                weak_sentences.append((i, sentence, results_with_metadata[:2]))
            else:
                status, priority = "Missing", "High"
                weak_sentences.append((i, sentence, results_with_metadata[:2]))

            rec = {
                "sentence": sentence[:500],
                "closest_control": best.get("text", "")[:300],
                "framework": best.get("framework", "Unknown"),
                "control_id": str(control_id),
                "section": str(section),
                "distance": round(1 - sim, 3),
                "similarity_score": round(sim, 3),
                "status": status,
                "priority": priority,
                "suggested_improvement": "",
                "metadata": {
                    "model_used": CONFIG["openai_model"],
                    "chunk_index": (best.get("metadata", {}) or {}).get("chunk_index"),
                    "embedding_hash": (best.get("metadata", {}) or {}).get("embedding_hash"),
                },
            }
            recommendations.append(rec)
            logger.info(f"✅ Processed sentence {i+1}/{len(policy_sentences)}: {status} (sim: {sim:.3f}) - Control: {control_id}")

        except Exception as e:
            logger.error(f"❌ Error processing sentence {i+1}: {e}")
            continue

    # Generate suggestions in batches for performance
    if weak_sentences:
        logger.info(f"🤖 Generating {len(weak_sentences)} AI suggestions using batch processing...")
        
        sentences_and_controls = [(sentence, results_with_metadata) for _, sentence, results_with_metadata in weak_sentences]
        
        batch_start = time.time()
        suggestions = suggest_improvement_batch(sentences_and_controls)
        batch_time = time.time() - batch_start
        
        logger.info(f"⚡ Generated {len(suggestions)} suggestions in {batch_time:.2f}s")
        
        # Update recommendations with suggestions
        for (_, sentence, _), suggestion in zip(weak_sentences, suggestions):
            for rec in recommendations:
                if rec["sentence"].startswith(sentence[:100]):
                    rec["suggested_improvement"] = suggestion[:400]
                    break

    executive_summary = generate_executive_summary(recommendations)
    
    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    # Clean up memory
    _optimize_memory_usage()
    
    report_data = {
        "executive_summary": executive_summary,
        "detailed_report": recommendations,
        "metadata": {
            "client_name": client_name,
            "document_name": document_name,
            "total_sentences": len(policy_sentences),
            "processed_sentences": len(recommendations),
            "total_recommendations": len(recommendations),
            "report_generated_at": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "processing_time_seconds": round(processing_time, 2),
            "model_used": CONFIG["openai_model"],
            "aligned_count": len([r for r in recommendations if r.get("status") == "Aligned"]),
            "weak_count": len([r for r in recommendations if r.get("status") == "Weak"]),
            "missing_count": len([r for r in recommendations if r.get("status") == "Missing"]),
            "high_priority_count": len([r for r in recommendations if r.get("priority") == "High"]),
            "medium_priority_count": len([r for r in recommendations if r.get("priority") == "Medium"]),
            "low_priority_count": len([r for r in recommendations if r.get("priority") == "Low"])
        }
    }

    logger.info(f"✅ Generated complete report: {len(recommendations)} recommendations in {processing_time:.2f}s")
    
    return report_data

def generate_executive_summary(recommendations: List[Dict[str, Any]]) -> str:
    """Generate executive summary with proper formatting"""
    if not isinstance(recommendations, list):
        return "No policy findings to report."
    
    recs = [r for r in recommendations if isinstance(r, dict)]
    total = len(recs)
    if total == 0:
        return "No policy findings to report."

    status_counts = {"Aligned": 0, "Weak": 0, "Missing": 0}
    priority_counts = {"High": 0, "Medium": 0, "Low": 0}
    framework_counts: Dict[str, int] = {}

    for r in recs:
        s = r.get("status", "Missing")
        p = r.get("priority", "High")
        status_counts[s] = status_counts.get(s, 0) + 1
        priority_counts[p] = priority_counts.get(p, 0) + 1
        framework_counts[r.get("framework", "Unknown")] = framework_counts.get(r.get("framework", "Unknown"), 0) + 1

    aligned_pct = round((status_counts["Aligned"] / total) * 100, 1)
    weak_pct = round((status_counts["Weak"] / total) * 100, 1)
    missing_pct = round((status_counts["Missing"] / total) * 100, 1)

    top_frameworks = sorted(framework_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    return (
        "EXECUTIVE SUMMARY - ComplyAI Analysis\n\n"
        f"Policy Statements Analyzed: {total}\n"
        f"• Aligned: {status_counts['Aligned']} ({aligned_pct}%)\n"
        f"• Needs Improvement: {status_counts['Weak']} ({weak_pct}%)\n"
        f"• Non-compliant: {status_counts['Missing']} ({missing_pct}%)\n\n"
        f"Priority Items:\n"
        f"• High: {priority_counts['High']}\n"
        f"• Medium: {priority_counts['Medium']}\n"
        f"• Low: {priority_counts['Low']}\n\n"
        f"Top Frameworks:\n" + 
        "\n".join([f"• {fw}: {count} matches" for fw, count in top_frameworks]) + "\n\n"
        f"NEXT STEPS:\n"
        f"1. Address {priority_counts['High']} high-priority gaps\n"
        f"2. Review {status_counts['Weak']} weak policies\n"
        f"3. Regular compliance monitoring recommended\n\n"
        f"Generated using {CONFIG['openai_model']}."
    )

def validate_configuration() -> bool:
    """Validate that all required configuration is present"""
    required_vars = ["OPENAI_API_KEY", "OPENAI_MODEL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    logger.info(f"✅ Configuration validated for {CONFIG['openai_model']}")
    return True

if not validate_configuration():
    logger.warning("⚠️ Configuration issues detected - some functionality may be limited")