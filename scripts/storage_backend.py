import os
from pathlib import Path
from typing import Optional

import requests


def supabase_storage_enabled() -> bool:
    return os.getenv("ENABLE_SUPABASE_STORAGE", "false").lower() == "true"


def _env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def upload_file_to_supabase(local_file_path: str, object_name: Optional[str] = None) -> Optional[str]:
    """
    Upload a file to Supabase Storage and return a public URL pattern.
    Requires ENABLE_SUPABASE_STORAGE=true and valid Supabase env vars.
    """
    if not supabase_storage_enabled():
        return None

    supabase_url = _env("SUPABASE_URL").rstrip("/")
    service_role_key = _env("SUPABASE_SERVICE_ROLE_KEY")
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "reports").strip() or "reports"

    file_path = Path(local_file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found for storage upload: {local_file_path}")

    object_key = object_name or file_path.name
    endpoint = f"{supabase_url}/storage/v1/object/{bucket}/{object_key}"

    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "x-upsert": "true",
        "Content-Type": "application/octet-stream",
    }

    with file_path.open("rb") as f:
        response = requests.post(endpoint, headers=headers, data=f.read(), timeout=60)

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Supabase storage upload failed ({response.status_code}): {response.text[:500]}"
        )

    # Works for public buckets. For private buckets, use signed URLs in a future iteration.
    return f"{supabase_url}/storage/v1/object/public/{bucket}/{object_key}"
