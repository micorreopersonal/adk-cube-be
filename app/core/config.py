from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_ID: str
    REGION: str = "us-central1"
    ENV: str = "development"  # "development" o "production"
    MODEL_NAME: str = "gemini-1.5-flash"
    
    # BigQuery
    BQ_DATASET: str
    BQ_TABLE_TURNOVER: str
    
    # Cloud Storage
    GCS_BUCKET_DOCS: str
    GCS_BUCKET_LANDING: str
    
    # Firestore
    FIRESTORE_COLLECTION: str = "agent_sessions"
    
    # App
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "adk-talent-analytics-super-secret-key-2026-sota-security"
    
    @property
    def APP_ENV(self):
        return self.ENV

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings():
    return Settings()
