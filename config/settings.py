# Create: config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "text-embedding-3-small"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    upload_timeout: int = 300  # 5 minutes
    batch_size: int = 50
    
    class Config:
        env_file = ".env"

settings = Settings()