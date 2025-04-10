# scripts/report_generator.py

from collections import Counter
import datetime

def generate_compliance_report(recommendations):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Normalize keys in case of inconsistent casing from earlier modules
    classifications = [r.get("Status") or r.get("status", "Unknown") for r in recommendations]
    classification_counts = Counter(classifications)

    executive_summary = {
        "report_generated_at": timestamp,
        "total_sentences_analyzed": len(recommendations),
        "Missing": classification_counts.get("Missing", 0),
        "Weak": classification_counts.get("Weak", 0),
        "Aligned": classification_counts.get("Aligned", 0),
        "recommendations_needed": classification_counts.get("Missing", 0) + classification_counts.get("Weak", 0)
    }

    detailed_report = []
    for rec in recommendations:
        detailed_report.append({
            "Policy Sentence": rec.get("Policy Sentence", "N/A"),
            "Status": rec.get("Status", "Unknown"),
            "Framework": rec.get("Framework", "Unknown"),
            "Closest Control": rec.get("Closest Control", "N/A"),
            "Score": rec.get("Score", 0),
            "Suggested Improvement": rec.get("Suggested Improvement") or rec.get("suggested_statement", "N/A")
        })

    return {
        "executive_summary": executive_summary,
        "detailed_report": detailed_report
    }
