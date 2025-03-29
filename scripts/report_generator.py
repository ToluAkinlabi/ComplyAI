# scripts/report_generator.py

from collections import Counter
import datetime

def generate_compliance_report(recommendations):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    classifications = [r['status'] for r in recommendations]
    classification_counts = Counter(classifications)

    # Executive Summary
    executive_summary = {
        "report_generated_at": timestamp,
        "total_sentences_analyzed": len(recommendations),
        "status_counts": dict(classification_counts),
        "recommendations_needed": classification_counts.get("Missing", 0) + classification_counts.get("Weak", 0)
    }

    # Control Coverage Report
    detailed_report = []
    for rec in recommendations:
        detailed_report.append({
            "Policy Sentence": rec['policy_sentence'],
            "Status": rec['status'],
            "Framework": rec['framework'],
            "Closest Control": rec['closest_control'],
            "Score": rec['score'],
            "Suggested Improvement": rec.get("suggested_statement", "N/A")
        })

    return {
        "executive_summary": executive_summary,
        "detailed_report": detailed_report
    }