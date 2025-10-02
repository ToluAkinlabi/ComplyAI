import hashlib

try:
    import magic
except ImportError:
    magic = None

class FileSecurityScanner:
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    
    def scan_file(self, file_path: str) -> dict:
        if magic is None:
            raise ImportError("python-magic is required for file type detection.")
        mime_type = magic.from_file(file_path, mime=True)
        if mime_type not in self.ALLOWED_MIME_TYPES:
            return {"mime_type": mime_type, "hash": None, "safe": False, "reason": "Forbidden file type"}
        file_hash = self._calculate_hash(file_path)
        return {"mime_type": mime_type, "hash": file_hash, "safe": True}
    
    def _calculate_hash(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()