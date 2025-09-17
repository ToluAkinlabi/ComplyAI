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


def suggest_improvement(policy_sentence: str, matched_control: str, framework_label: str) -> str:
        prompt = f"""
    You are a cybersecurity policy expert. Given this CONTROL from the "{framework_label}" framework:

    \"\"\"{matched_control}\"\"\"

    Please draft a NEW policy statement that a company can adopt to comply with the control above. 
    Do not rephrase the input policy, and ignore any policy fragments provided. 
    Use only the control as your source of truth.
    """
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
            "Priority": priority
        }

        report.append(recommendation)

    # Generate suggestions for top 5 weak/missing items
    suggestion_candidates = [r for r in report if r["Status"] in ["Missing", "Weak"]][:5]

    for rec in suggestion_candidates:
        rec["Suggested Improvement"] = suggest_improvement(
            rec["Policy Sentence"], rec["Closest Control"], rec["Framework"]
        )

    executive_summary = {
        "Total Sentences": len(policy_sentences),
        "Missing": sum(1 for r in report if r["Status"] == "Missing"),
        "Weak": sum(1 for r in report if r["Status"] == "Weak"),
        "Aligned": sum(1 for r in report if r["Status"] == "Aligned"),
        "report_generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return executive_summary, report
