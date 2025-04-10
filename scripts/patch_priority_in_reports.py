# scripts/patch_priority_in_reports.py

import os
import json
from datetime import datetime

from scripts.recommendation_engine import classify_distance, determine_priority

REPORTS_DIR = "reports"
patched = 0
skipped = 0

for filename in os.listdir(REPORTS_DIR):
    if not filename.endswith(".json"):
        continue

    path = os.path.join(REPORTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        try:
            report = json.load(f)
        except json.JSONDecodeError:
            print(f"❌ Skipped malformed JSON: {filename}")
            continue

    if not report.get("detailed_report"):
        print(f"⚠️  Skipped empty report: {filename}")
        skipped += 1
        continue

    updated = False
    for rec in report["detailed_report"]:
        if "Priority" not in rec or not rec["Priority"]:
            score = rec.get("Score", 0.0)
            status = rec.get("Status", classify_distance(score))
            rec["Priority"] = determine_priority(status, score)
            updated = True

    if updated:
        report["executive_summary"]["report_generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"✅ Patched: {filename}")
        patched += 1
    else:
        print(f"⏭ No changes needed: {filename}")
        skipped += 1

print(f"🎯 Done. Patched: {patched} | Skipped: {skipped}")