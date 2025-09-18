import os
from dotenv import load_dotenv
import openai
from datetime import datetime
from more_itertools import chunked
from scripts.semantic_engine import group_semantic_sentences

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

VERBOSE = True  # Set to False to silence logs


def classify_distance(distance: float) -> str:
    if distance > 0.5:
        return "Missing"
    elif 0.3 < distance <= 0.5:
        return "Weak"
    elif distance <= 0.3:
        return "Aligned"
    return "Unknown"


def determine_priority(status: str, score: float) -> str:
    if status == "Missing" and score > 0.75:
        return "High"
    elif status == "Missing":
        return "Medium"
    elif status == "Weak" and score > 0.45:
        return "Medium"
    elif status == "Weak":
        return "Low"
    return "Low"


def suggest_improvement(policy_sentence: str, matched_control: str, framework_label: str, top_controls: list = None) -> str:
    # RAG-style: use top-N controls for richer context
    if top_controls is None:
        top_controls = [(matched_control, framework_label)]
    controls_text = "\n\n".join([
        f"[{i+1}] ({label}) {ctrl}" for i, (ctrl, label) in enumerate(top_controls)
    ])
    prompt = (
        f"You are a cybersecurity policy expert. Given the following CONTROLS from the \"{framework_label}\" framework:\n\n"
        f"{controls_text}\n\n"
        f"The original policy statement is:\n\n"
        f"{policy_sentence}\n\n"
        "Please draft a NEW policy statement that a company can adopt to comply with the above controls. "
        "Use only the controls as your source of truth. If you use a specific control, cite it by its number in your answer. "
        "If you cannot confidently suggest a compliant policy, say so."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        suggestion = response.choices[0].message.content.strip()
        return suggestion
    except Exception as e:
        if VERBOSE:
            print(f"❌ GPT error: {e}")
        return "Unable to generate suggestion. Please review manually."


def generate_recommendations(policy_sentences, D, I, framework_sentences, framework_labels):
    report = []

    if VERBOSE:
        print("🔍 Classifying semantic matches...")

    grouped_sentences = group_semantic_sentences(policy_sentences, threshold=0.65)
    for idx, sentence in enumerate(grouped_sentences):
        if idx >= len(D) or idx >= len(I) or len(D[idx]) == 0 or len(I[idx]) == 0:
            continue

        # Get top-3 controls for RAG context
        top_n = 3
        top_indices = list(I[idx][:top_n])
        top_controls = [(framework_sentences[i], framework_labels[i]) for i in top_indices]

        closest_distance = float(D[idx][0])
        matched_idx = int(I[idx][0])

        status = classify_distance(closest_distance)
        priority = determine_priority(status, closest_distance)

        recommendation = {
            "Policy Sentence": sentence,
            "Status": status,
            "Framework": framework_labels[matched_idx],
            "Closest Control": framework_sentences[matched_idx],
            "Score": round(closest_distance, 3),
            "Priority": priority,
            "Top Controls": top_controls
        }

        report.append(recommendation)

    # Generate suggestions for top 5 weak/missing items
    suggestion_candidates = [r for r in report if r["Status"] in ["Missing", "Weak"]][:5]

    for rec in suggestion_candidates:
        rec["Suggested Improvement"] = suggest_improvement(
            rec["Policy Sentence"], rec["Closest Control"], rec["Framework"], rec.get("Top Controls")
        )

    executive_summary = {
        "Total Sentences": len(policy_sentences),
        "Missing": sum(1 for r in report if r["Status"] == "Missing"),
        "Weak": sum(1 for r in report if r["Status"] == "Weak"),
        "Aligned": sum(1 for r in report if r["Status"] == "Aligned"),
        "report_generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return executive_summary, report
