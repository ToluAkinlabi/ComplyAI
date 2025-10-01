import os
import logging
from typing import List, Dict, Any

from scripts.semantic_engine import semantic_engine
from scripts.framework_loader import load_frameworks  # NEW: bootstrap if index missing

# Load environment variables (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CONFIG = {
    "openai_model": os.getenv("OPENAI_MODEL", "gpt-4"),
    "max_completion_tokens": int(os.getenv("MAX_COMPLETION_TOKENS", "300")),
    "temperature_env": os.getenv("OPENAI_TEMPERATURE", "1"),
    "aligned_threshold": float(os.getenv("ALIGNED_THRESHOLD", "0.7")),
    "weak_threshold": float(os.getenv("WEAK_THRESHOLD", "0.4")),
    "max_suggestions": int(os.getenv("MAX_SUGGESTIONS", "5")),
}

# Parse temperature once
try:
    CONFIG["temperature"] = float(CONFIG["temperature_env"])
except Exception:
    CONFIG["temperature"] = None

# OpenAI client (new vs legacy)
OPENAI_NEW_API = False
client = None
OPENAI_API_READY = False

try:
    import openai

    if hasattr(openai, "OpenAI"):
        # New SDK style: client = openai.OpenAI(...)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        client = openai.OpenAI(api_key=api_key)
        OPENAI_NEW_API = True
        OPENAI_API_READY = True
        logger.info(f"OpenAI new API initialized. Model={CONFIG['openai_model']}")
    else:
        # Legacy style: openai.ChatCompletion.create(...)
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        OPENAI_NEW_API = False
        OPENAI_API_READY = True
        logger.info(f"OpenAI legacy API initialized. Model={CONFIG['openai_model']}")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    OPENAI_API_READY = False


def _call_llm_with_retry(prompt: str) -> str:
    """
    Calls OpenAI chat API with robust fallbacks.
    - Some models reject custom temperature (e.g., allow only default=1)
    - Some models reject max_tokens (or prefer max_completion_tokens)
    We try combinations and fall back to minimal params.
    """
    if not OPENAI_API_READY:
        logger.warning("OpenAI API not configured; returning stub suggestion.")
        return "LLM unavailable. Please review this control manually."

    messages = [{"role": "user", "content": prompt}]
    temp = CONFIG["temperature"]
    max_tok = CONFIG["max_completion_tokens"]

    def do_call_new(include_temp: bool, tok_param: str | None):
        # tok_param in { "max_tokens", "max_completion_tokens", None }
        params = {
            "model": CONFIG["openai_model"],
            "messages": messages,
        }
        if tok_param == "max_tokens":
            params["max_tokens"] = max_tok
        elif tok_param == "max_completion_tokens":
            params["max_completion_tokens"] = max_tok

        # Only pass temperature if explicitly 1.0 (default) or model allows it
        if include_temp and temp is not None and float(temp) == 1.0:
            params["temperature"] = 1.0

        return client.chat.completions.create(**params)

    def do_call_legacy(include_temp: bool):
        params = {
            "model": CONFIG["openai_model"],
            "messages": messages,
            "max_tokens": max_tok,
        }
        if include_temp and temp is not None and float(temp) == 1.0:
            params["temperature"] = 1.0
        return openai.ChatCompletion.create(**params)

    try:
        if OPENAI_NEW_API:
            # 1) Try with max_completion_tokens and default temp only
            return (do_call_new(include_temp=True, tok_param="max_completion_tokens")
                    .choices[0].message.content.strip())
        else:
            # Legacy: try once with max_tokens and default temp only
            return (do_call_legacy(include_temp=True)
                    .choices[0].message.content.strip())
    except Exception as e1:
        msg1 = str(e1).lower()
        logger.info(f"Retry path 1 triggered: {msg1}")

        try:
            if OPENAI_NEW_API:
                # 2) Remove temperature, keep max_completion_tokens
                return (do_call_new(include_temp=False, tok_param="max_completion_tokens")
                        .choices[0].message.content.strip())
            else:
                # Legacy: remove temperature (we didn't add unless 1.0), so just re-try w/ same params
                return (do_call_legacy(include_temp=False)
                        .choices[0].message.content.strip())
        except Exception as e2:
            msg2 = str(e2).lower()
            logger.info(f"Retry path 2 triggered: {msg2}")

            try:
                if OPENAI_NEW_API:
                    # 3) Switch to max_tokens (some chat endpoints want this)
                    return (do_call_new(include_temp=False, tok_param="max_tokens")
                            .choices[0].message.content.strip())
                else:
                    # Legacy: already using max_tokens; try minimal
                    return openai.ChatCompletion.create(
                        model=CONFIG["openai_model"],
                        messages=messages
                    ).choices[0].message.content.strip()
            except Exception as e3:
                msg3 = str(e3).lower()
                logger.info(f"Retry path 3 triggered: {msg3}")

                try:
                    if OPENAI_NEW_API:
                        # 4) Minimal: no temp, no token limits
                        return client.chat.completions.create(
                            model=CONFIG["openai_model"],
                            messages=messages
                        ).choices[0].message.content.strip()
                    else:
                        # Legacy minimal
                        return openai.ChatCompletion.create(
                            model=CONFIG["openai_model"],
                            messages=messages
                        ).choices[0].message.content.strip()
                except Exception as e4:
                    logger.error(f"All LLM attempts failed: {e4}")
                    return "Unable to generate suggestion due to model parameter restrictions."


def suggest_improvement(sentence: str, closest_controls_with_metadata: List[Dict]) -> str:
    try:
        if not closest_controls_with_metadata:
            return "No relevant controls found for improvement suggestion."

        # Build a grounded, framework-driven context (not a rephrase of sentence)
        context_parts, citations = [], []
        for i, control_data in enumerate(closest_controls_with_metadata[:3], 1):
            if not isinstance(control_data, dict):
                continue
            control_text = control_data.get("text", "Unknown")
            framework = control_data.get("framework", "Unknown")
            control_id = control_data.get("control_id", "Unknown")
            section = control_data.get("section", "General")
            confidence = float(control_data.get("similarity_score", 0.0) or 0.0)

            context_parts.append(
                f"Control {i} [{framework} - {control_id}]\n"
                f"Section: {section}\n"
                f"Confidence: {confidence:.2f}\n"
                f"Text: {control_text}\n"
            )
            citations.append(f"{framework} - {control_id}")

        if not context_parts:
            return "Insufficient framework guidance for specific improvement."

        prompt = (
            "You are a cybersecurity compliance expert. Using ONLY the following framework controls, "
            "draft a clear, specific policy statement that would bring the organization into compliance. "
            "Do not rephrase the original policy text; derive the improvement from the controls.\n\n"
            f"ORIGINAL POLICY SENTENCE:\n{sentence}\n\n"
            "RELEVANT FRAMEWORK CONTROLS:\n"
            + "\n\n".join(context_parts)
            + "\n\nREQUIREMENTS:\n"
            "1) Ground the improvement in the control language\n"
            "2) Be precise and actionable (non-generic)\n"
            "3) Cite which control(s) you used: " + ", ".join(citations) + "\n"
            "4) If controls are insufficient, say: 'Insufficient framework guidance for specific improvement'\n\n"
            "IMPROVED POLICY:\n"
        )

        return _call_llm_with_retry(prompt)
    except Exception as e:
        logger.error(f"Error preparing suggestion prompt: {e}")
        return "Unable to generate suggestion due to an error."


def _bootstrap_index_if_needed() -> None:
    """Ensure the FAISS index is available so we don't return empty output."""
    if getattr(semantic_engine, "index", None) is not None:
        return
    try:
        fw_data = load_frameworks()
        if not fw_data:
            logger.error("No frameworks loaded; cannot build index.")
            return
        semantic_engine.build_enhanced_index(fw_data)
        logger.info("Semantic index bootstrapped inside recommendation_engine.")
    except Exception as e:
        logger.error(f"Failed to bootstrap index: {e}")


def generate_recommendations(policy_sentences: List[str]) -> List[Dict[str, Any]]:
    _bootstrap_index_if_needed()
    if getattr(semantic_engine, "index", None) is None:
        logger.error("Semantic engine not initialized; returning no recommendations.")
        return []

    recommendations: List[Dict[str, Any]] = []

    for sentence in policy_sentences:
        try:
            results_with_metadata = semantic_engine.retrieve_with_metadata(
                sentence, top_k=CONFIG["max_suggestions"]
            )
            if not isinstance(results_with_metadata, list) or not results_with_metadata:
                continue

            best = results_with_metadata[0]
            if not isinstance(best, dict):
                continue

            sim = float(best.get("similarity_score", 0.0) or 0.0)
            if sim >= CONFIG["aligned_threshold"]:
                status, priority = "Aligned", "Low"
            elif sim >= CONFIG["weak_threshold"]:
                status, priority = "Weak", "Medium"
            else:
                status, priority = "Missing", "High"

            suggestion = ""
            if status in ("Missing", "Weak"):
                suggestion = suggest_improvement(sentence, results_with_metadata)

            rec = {
                "sentence": sentence,
                "closest_control": best.get("text", ""),
                "framework": best.get("framework", "Unknown"),
                "control_id": best.get("control_id", "Unknown"),
                "section": best.get("section", "General"),
                "distance": round(1 - sim, 3),
                "similarity_score": round(sim, 3),
                "status": status,
                "priority": priority,
                "suggested_improvement": suggestion,
                "metadata": {
                    "model_used": CONFIG["openai_model"],
                    "chunk_index": (best.get("metadata", {}) or {}).get("chunk_index"),
                    "embedding_hash": (best.get("metadata", {}) or {}).get("embedding_hash"),
                },
            }
            recommendations.append(rec)
        except Exception as e:
            logger.error(f"Error processing sentence '{sentence[:90]}': {e}")

    logger.info(f"✅ Generated {len(recommendations)} recommendations using {CONFIG['openai_model']}")
    return recommendations


def generate_executive_summary(recommendations: List[Dict[str, Any]]) -> str:
    if not isinstance(recommendations, list):
        return "No policy findings to report."
    recs = [r for r in recommendations if isinstance(r, dict)]
    total = len(recs)
    if total == 0:
        return "No policy findings to report."

    status_counts = {"Aligned": 0, "Weak": 0, "Missing": 0}
    priority_counts = {"High": 0, "Medium": 0, "Low": 0}
    framework_counts: Dict[str, int] = {}
    status_sims: Dict[str, List[float]] = {"Aligned": [], "Weak": [], "Missing": []}

    for r in recs:
        s = r.get("status", "Missing")
        p = r.get("priority", "High")
        status_counts[s] = status_counts.get(s, 0) + 1
        priority_counts[p] = priority_counts.get(p, 0) + 1
        framework_counts[r.get("framework", "Unknown")] = framework_counts.get(r.get("framework", "Unknown"), 0) + 1
        status_sims.setdefault(s, []).append(float(r.get("similarity_score", 0.0) or 0.0))

    def avg(xs: List[float]) -> float:
        return round(sum(xs) / len(xs), 2) if xs else 0.0

    aligned_pct = round((status_counts["Aligned"] / total) * 100, 1)
    weak_pct = round((status_counts["Weak"] / total) * 100, 1)
    missing_pct = round((status_counts["Missing"] / total) * 100, 1)

    top_frameworks = sorted(framework_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    return (
        "EXECUTIVE SUMMARY - Enhanced ComplyAI Analysis\n\n"
        f"Policy Compliance Analysis Results:\n"
        f"• Total Policy Statements Analyzed: {total}\n"
        f"• Aligned with Framework Controls: {status_counts['Aligned']} ({aligned_pct}%) - Avg Confidence: {avg(status_sims['Aligned'])}\n"
        f"• Weakly Aligned (Needs Improvement): {status_counts['Weak']} ({weak_pct}%) - Avg Confidence: {avg(status_sims['Weak'])}\n"
        f"• Missing/Non-compliant: {status_counts['Missing']} ({missing_pct}%) - Avg Confidence: {avg(status_sims['Missing'])}\n\n"
        f"Priority Distribution:\n"
        f"• High Priority Items: {priority_counts['High']}\n"
        f"• Medium Priority Items: {priority_counts['Medium']}\n"
        f"• Low Priority Items: {priority_counts['Low']}\n\n"
        f"Top Referenced Frameworks:\n" + "\n".join([f"• {fw}: {count} matches" for fw, count in top_frameworks]) + "\n"
    )
