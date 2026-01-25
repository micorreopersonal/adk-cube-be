from google.adk.sessions import BaseSessionService, Session
from google.cloud import firestore
from app.services.firestore import get_firestore_service
from typing import Optional, Any

class FirestoreADKSessionService(BaseSessionService):
    """
    Adaptador que implementa la interfaz SessionService de ADK
    usando nuestro backend FirestoreService existente.
    """
    def __init__(self):
        self.firestore = get_firestore_service()

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[Any] = None, # BaseSessionService define config type hint
    ) -> Optional[Session]:
        """Recupera la sesión desde Firestore y la convierte a objeto Session ADK."""
        data = await self.firestore.get_session(session_id)
        if not data:
            return None
            
        # Reconstruir objeto Session desde dict
        # NOTA: ADK Session usa 'id' y 'events'. Firestore usaba 'session_id' y 'history'.
        return Session(
            app_name=data.get("app_name", app_name),
            user_id=data.get("user_id", user_id),
            id=session_id, # Pydantic field is 'id'
            events=data.get("history", []), # Pydantic field is 'events' (mapped from legacy 'history' in DB)
            state=data.get("state", {})
        )

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Crea una nueva sesión."""
        if not session_id:
             # Fallback simple si no viene ID (aunque ADK suele mandarlo o se genera)
             import uuid
             session_id = str(uuid.uuid4())
             
        session = Session(
            app_name=app_name, 
            user_id=user_id, 
            id=session_id, # Pydantic field is 'id'
            state=state or {}
        )
        # Guardar estado inicial
        await self.save_session_data(session)
        return session

    async def list_sessions(self, *, app_name: str, user_id: Optional[str] = None):
        """Lista sesiones (No implementado en backend actual de Firestore simple)."""
        # Retornamos estructura vacía válida para cumplir contrato
        from google.adk.sessions.base_session_service import ListSessionsResponse
        return ListSessionsResponse(sessions=[])

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        """Borra una sesión (No-op por seguridad en esta fase)."""
        pass

    # --- Método Auxiliar de Persistencia ---
    async def save_session_data(self, session: Session):
        """Helper para guardar datos en Firestore."""
        data = {
            "app_name": session.app_name,
            "user_id": session.user_id,
            "session_id": session.id, # DB seguirá usando session_id como key para compatibilidad
            # Serializar eventos/history. 
            "history": [self._serialize_event(e) for e in session.events], # Guardar en DB como 'history'
            "state": session.state,
            "updated_at": firestore.SERVER_TIMESTAMP # Para TTL Policy
        }
        await self.firestore.save_session(session.id, data)

    def _serialize_event(self, event):
        # Helper simple para serializar eventos si son objetos
        if hasattr(event, "model_dump"): return event.model_dump()
        if hasattr(event, "to_dict"): return event.to_dict()
        return event

    # Override append_event para persistir cambios
    async def append_event(self, session: Session, event: Any) -> Any:
        # Llamar a base para actualizar objeto en memoria
        result = await super().append_event(session, event)
        # Persistir cambio en DB
        await self.save_session_data(session)
        return result
