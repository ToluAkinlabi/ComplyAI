# Add: scripts/cache_manager.py
import redis
import pickle
from typing import Optional, Any

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    def get_document_analysis(self, file_hash: str) -> Optional[dict]:
        cached = self.redis_client.get(f"analysis:{file_hash}")
        return pickle.loads(cached) if cached else None
    
    def set_document_analysis(self, file_hash: str, analysis: dict, ttl: int = 3600):
        self.redis_client.setex(f"analysis:{file_hash}", ttl, pickle.dumps(analysis))