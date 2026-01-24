from google.cloud import storage
from app.core.config import get_settings

class CloudStorageService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CloudStorageService, cls).__new__(cls)
            cls._instance._client = None
        return cls._instance

    @property
    def client(self) -> storage.Client:
        if self._client is None:
            settings = get_settings()
            self._client = storage.Client(project=settings.PROJECT_ID)
        return self._client

    def download_as_string(self, bucket_name: str, blob_name: str) -> str:
        """Descarga un objeto de GCS como string."""
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.download_as_text()

    def upload_from_string(self, bucket_name: str, blob_name: str, data: str, content_type: str = "text/plain"):
        """Sube un string a GCS."""
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(data, content_type=content_type)

def get_storage_service():
    return CloudStorageService()
