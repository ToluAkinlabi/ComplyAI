# Add: scripts/task_queue.py
from celery import Celery
from typing import List

celery_app = Celery('complyai', broker='redis://localhost:6379')

@celery_app.task
def process_document_async(file_path: str, client_name: str) -> dict:
    """Process document asynchronously for large files"""
    # ... processing logic ...
    return analysis_result