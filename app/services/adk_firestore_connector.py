from google.adk.sessions import BaseSessionService, Session
from app.services.firestore import get_firestore_service
from typing import Optional

class FirestoreADKSessionService(BaseSessionService):
    """
    Adaptador que implementa la interfaz SessionService de ADK
    usando nuestro backend FirestoreService existente.
    """
    def __init__(self):
        self.firestore = get_firestore_service()

    async def get_session(self, app_name: str, user_id: str, session_id: str) -> Optional[Session]:
        """Recupera la sesión desde Firestore y la convierte a objeto Session ADK."""
        # Clave compuesta para evitar colisiones si se usa misma session_id en distinta app
        # Pero por simplicidad y compatibilidad con nuestro diseño simple, usamos session_id directo
        # o construimos una key. Seguiremos el patrón de document_id = session_id directo
        # como estaba en firestore.py original.
        
        data = await self.firestore.get_session(session_id)
        if not data:
            return None
            
        # Reconstruir objeto Session desde dict
        return Session(
            app_name=data.get("app_name", app_name),
            user_id=data.get("user_id", user_id),
            session_id=session_id,
            history=data.get("history", []),
            state=data.get("state", {})
        )

    async def create_session(self, app_name: str, user_id: str, session_id: str) -> Session:
        """Crea una nueva sesión."""
        session = Session(app_name=app_name, user_id=user_id, session_id=session_id)
        # Guardar estado inicial vacío
        await self.save_session(session)
        return session

    async def save_session(self, session: Session):
        """Persiste la sesión en Firestore."""
        data = {
            "app_name": session.app_name,
            "user_id": session.user_id,
            "session_id": session.session_id,
            "history": session.history, # ADK maneja esto como lista de dicts
            "state": session.state
        }
        await self.firestore.save_session(session.session_id, data)

    async def delete_session(self, app_name: str, user_id: str, session_id: str):
        # Implementación opcional si ADK la requiere, por ahora pass o warning
        pass
