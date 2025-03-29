# scripts/recommendation_engine.py
# This script will generate recommendations based on the semantic matching results between policy documents and cybersecurity frameworks. It will classify the distance between matched sentences and provide a report of recommendations.

import os
from dotenv import load_dotenv
import openai

load_dotenv()

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

    for idx, sentence in enumerate(policy_sentences):
        closest_distance = float(D[idx][0])
        matched_index = I[idx][0]
        framework = framework_labels[matched_index]
        matched_sentence = framework_sentences[matched_index]

        classification = classify_distance(closest_distance)

        recommendation = {
            "policy_sentence": sentence,
            "status": classification,
            "closest_control": matched_sentence,
            "framework": framework,
            "score": closest_distance
        }
        report.append(recommendation)

    # Limit GPT-4 calls to top 5 weak/missing
    recommendation_candidates = [r for r in report if r["status"] in ["Missing", "Weak"]][:5]

    for rec in recommendation_candidates:
        rec["suggested_statement"] = suggest_improvement(rec["policy_sentence"], rec["closest_control"])

    return report


openai.api_key = os.getenv("OPENAI_API_KEY")

def suggest_improvement(policy_sentence, matched_control):
    prompt = f""" 
    The following policy sentence seems weak or missing compared to the recommended control.

    Policy: "{policy_sentence}"
    Recommended Control: "{matched_control}"

    Suggest a professionally worded policy statement that would align better with industry best practices.
    """

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    suggestion = completion['choices'][0]['message']['content'].strip()
    return suggestion
