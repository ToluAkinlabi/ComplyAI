import os
from dotenv import load_dotenv
import openai

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


def suggest_improvement(policy_sentence: str, matched_sentence: str) -> str:
    prompt = f""" 
The following policy sentence seems weak or missing compared to the recommended control.

Policy: "{policy_sentence}"
Recommended Control: "{matched_sentence}"

Suggest a professionally worded policy statement that would align better with industry best practices.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
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

    for idx, sentence in enumerate(policy_sentences):
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
            rec["Policy Sentence"], rec["Closest Control"]
        )

    executive_summary = {
        "Total Sentences": len(policy_sentences),
        "Missing": sum(1 for r in report if r["Status"] == "Missing"),
        "Weak": sum(1 for r in report if r["Status"] == "Weak"),
        "Aligned": sum(1 for r in report if r["Status"] == "Aligned"),
        "report_generated_at": os.getenv("REPORT_TIMESTAMP", "Not Specified")
    }

    return executive_summary, report
