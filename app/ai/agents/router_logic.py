from google.adk import Runner
import os
# from google.adk.sessions.in_memory_session_service import InMemorySessionService (Removed)
from google.genai import types, Client
from app.ai.agents.hr_agent import get_hr_agent
from app.core.config import get_settings

from app.services.adk_firestore_connector import FirestoreADKSessionService

class AgentRouter:
    """
    Orquestador principal que redirige las consultas a los agentes especialistas.
    Usa el Runner de ADK para manejar la sesión y la ejecución del agente.
    """
    def __init__(self):
        self.session_service = FirestoreADKSessionService() # Integración Firestore real
        self.name = "ADK Router"
        settings = get_settings()
        
        # Cliente explícito para GenAI SDK (Vertex AI Mode)
        self.client = Client(
            vertexai=True, 
            project=settings.PROJECT_ID, 
            location=settings.REGION,
            http_options={'api_version': 'v1'} 
        )

    async def route(self, message: str, session_id: str = "default", profile: str = "EJECUTIVO") -> str:
        """
        Ejecuta la consulta a través de un Runner configurado para el perfil del usuario.
        """
        user_id = "default_user"
        app_name = "PeopleAnalyticsApp"

        # 1. Obtener agente especializado para el perfil
        specialized_agent = get_hr_agent(profile=profile)

        # Asegurar variables de entorno para inicialización implícita del cliente GenAI de ADK (Vertex AI Mode)
        settings = get_settings()
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        os.environ["GOOGLE_CLOUD_PROJECT"] = settings.PROJECT_ID
        os.environ["GOOGLE_CLOUD_LOCATION"] = settings.REGION

        # 2. Inicializar Runner dinámico
        runner = Runner(
            app_name=app_name,
            agent=specialized_agent,
            session_service=self.session_service
        )

        # 3. Preparar mensaje
        if profile:
            instruction_prefix = f"[INSTRUCCIÓN DE PERFIL: Responde asumiendo que el usuario es '{profile}'.]\n\n"
            full_message = instruction_prefix + message
        else:
            full_message = message

        new_message = types.Content(parts=[types.Part(text=full_message)], role="user")
        
        # 4. Asegurar sesión (Confirmado Async)
        if not await self.session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id):
            await self.session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)

        # 5. Ejecutar
        response_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
        
        return response_text or "No se pudo generar una respuesta."

def get_router():
    return AgentRouter()
