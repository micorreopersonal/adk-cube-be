from google.adk import Runner
import os
import asyncio
import time
import logging
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
        settings = get_settings()
        self.session_service = FirestoreADKSessionService() # Integración Firestore real
        self.name = "ADK Router"
        # Configurar logging básico
        logging.basicConfig(level=settings.LOG_LEVEL)
        self.logger = logging.getLogger("AgentRouter")
        
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

        # 5. Ejecutar con Estrategia de Reintento (Resiliencia ante 429)
        max_retries = 3
        retry_delay = 2 # segundos iniciales
        
        # Variables de telemetría
        total_api_calls = 0
        tools_called = []
        
        for attempt in range(max_retries):
            response_text = ""
            last_tool_result = None
            turn_count = 0
            
            try:
                self.logger.info(f"--- Starting Runner for session {session_id} (Attempt {attempt+1}/{max_retries}) ---")
                
                # Turn counting logic: A turn starts at the beginning of the run 
                # and after each tool call result is processed.
                current_turn_counted = False
                
                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=new_message
                ):
                    if event.content and event.content.parts:
                        # If we get content, and we haven't counted this turn yet, count it
                        if not current_turn_counted:
                            turn_count += 1
                            current_turn_counted = True
                        
                        for part in event.content.parts:
                            if part.text:
                                response_text += part.text
                            
                            if part.function_call:
                                total_api_calls += 1 
                                tools_called.append(part.function_call.name)
                                self.logger.info(f"[PROFILER] AI requested tool: {part.function_call.name}")
                                # After a function call, a new call will follow to process the result
                                current_turn_counted = False

                            if part.function_response:
                                try:
                                    if hasattr(part.function_response, 'response'):
                                        res = part.function_response.response
                                        last_tool_result = res.get('result', res)
                                except Exception as e:
                                    self.logger.error(f"Error capturing tool result: {e}")
                
                self.logger.info(f"[PROFILER] Session {session_id} - Total Model Turns: {turn_count} | Tools: {tools_called}")
                break

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        self.logger.warning(f"Quota exhausted (429). Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        self.logger.error("Max retries reached for 429 error.")
                        return "Lo siento, la cuota de la API de IA se ha agotado. Por favor, intenta de nuevo en unos minutos."
                else:
                    self.logger.error(f"Runner failed: {e}")
                    raise e

        print(f"--- [DEBUG] Final Response Length: {len(response_text)} ---")
        
        # 6. Lógica de Respuesta Prioritaria (VisualDataPackage First)
        if last_tool_result and isinstance(last_tool_result, dict):
            if last_tool_result.get("response_type") == "visual_package":
                # Inyectar telemetría para visibilidad en el frontend
                last_tool_result["telemetry"] = {
                    "model_turns": turn_count,
                    "tools_executed": tools_called,
                    "api_invocations_est": 1 + len(tools_called)
                }
                return last_tool_result

        # Fallback Logic
        if not response_text and last_tool_result:
            return last_tool_result
        
        return response_text or "No se pudo generar una respuesta."

def get_router():
    return AgentRouter()
