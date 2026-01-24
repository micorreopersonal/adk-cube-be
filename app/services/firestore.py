from google.cloud import firestore
from app.core.config import get_settings

class FirestoreService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirestoreService, cls).__new__(cls)
            cls._instance._client = None
        return cls._instance

    @property
    def client(self) -> firestore.AsyncClient:
        if self._client is None:
            settings = get_settings()
            self._client = firestore.AsyncClient(
                project=settings.PROJECT_ID,
                database="adk-pa-firestore-db" # Base de datos específica del usuario
            )
        return self._client

    async def save_session(self, session_id: str, data: dict):
        """Guarda o actualiza una sesión en Firestore."""
        settings = get_settings()
        doc_ref = self.client.collection(settings.FIRESTORE_COLLECTION).document(session_id)
        await doc_ref.set(data, merge=True)

    async def get_session(self, session_id: str) -> dict:
        """Recupera los datos de una sesión."""
        settings = get_settings()
        doc_ref = self.client.collection(settings.FIRESTORE_COLLECTION).document(session_id)
        doc = await doc_ref.get()
        return doc.to_dict() if doc.exists else None

def get_firestore_service():
    return FirestoreService()
