# models/frameworks.py
# This module handles the loading and processing of cybersecurity frameworks.


import os
import json

FRAMEWORKS_DIR = "./data/frameworks"

def load_all_frameworks():
    frameworks_data = []

    for filename in os.listdir(FRAMEWORKS_DIR):
        if filename.endswith(".json"):
            path = os.path.join(FRAMEWORKS_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                frameworks_data.append(data)

    return frameworks_data
