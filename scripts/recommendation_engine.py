# scripts/recommendation_engine.py
# This script will generate recommendations based on the semantic matching results between policy documents and cybersecurity frameworks. It will classify the distance between matched sentences and provide a report of recommendations.

import os
from dotenv import load_dotenv
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def classify_distance(distance):
    if distance > 0.6:
        return "Missing"
    elif 0.4 < distance <= 0.6:
        return "Weak"
    elif distance <= 0.4:
        return "Aligned"
    else:
        return "Unknown"


def generate_recommendations(policy_sentences, D, I, framework_sentences, framework_labels):
    report = []

    # Protect against FAISS returning less than expected
    if D.shape[1] < 1:
        raise ValueError("FAISS search returned no nearest neighbors. Is your index built correctly?")

    for idx, sentence in enumerate(policy_sentences):
        if idx >= len(D) or idx >= len(I) or len(D[idx]) == 0 or len(I[idx]) == 0:
            continue

        closest_distance = float(D[idx][0])
        matched_idx = int(I[idx][0])

        framework = framework_labels[matched_idx]
        matched_sentence = framework_sentences[matched_idx]

        classification = classify_distance(closest_distance)

        recommendation = {
            "Policy Sentence": sentence,
            "Status": classification,
            "Closest Control": matched_sentence,
            "Framework": framework,
            "Score": closest_distance
        }
        report.append(recommendation)

    # Limit GPT calls to top 5 weak/missing
    recommendation_candidates = [r for r in report if r["Status"] in ["Missing", "Weak"]][:5]

    for rec in recommendation_candidates:
        rec["suggested_statement"] = suggest_improvement(rec["Policy Sentence"], rec["Closest Control"])

    # Return both executive summary and full report
    executive_summary = {
        "Total Sentences": len(policy_sentences),
        "Missing": sum(1 for r in report if r["Status"] == "Missing"),
        "Weak": sum(1 for r in report if r["Status"] == "Weak"),
        "Aligned": sum(1 for r in report if r["Status"] == "Aligned"),
    }

    return executive_summary, report


def suggest_improvement(policy_sentences, matched_sentence):
    prompt = f""" 
    The following policy sentence seems weak or missing compared to the recommended control.

    Policy: "{policy_sentences}"
    Recommended Control: "{matched_sentence}"

    Suggest a professionally worded policy statement that would align better with industry best practices.
    """

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    suggestion = completion['choices'][0]['message']['content'].strip()
    return suggestion
