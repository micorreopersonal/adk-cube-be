from google.adk import Runner
import os
import asyncio
import time
import random
import logging
import re
import traceback
from google.genai import types, Client
from google.adk.events.event import Event
from app.ai.agents.hr_agent import get_hr_agent
from app.core.config.config import get_settings
from app.ai.tools.triage_validator import validate_dimensions, list_organizational_units

from app.services.adk_firestore_connector import FirestoreADKSessionService

class AgentRouter:
    """
    Orquestador principal que redirige las consultas a los agentes especialistas.
    Usa el Runner de ADK para manejar la sesión y la ejecución del agente.
    """
    _request_timestamps = [] # Class-level variable to track RPM across instances

    def __init__(self):
        settings = get_settings()
        self.session_service = FirestoreADKSessionService() # Integración Firestore real
        self.name = "ADK Router"
        # Configurar logging básico
        logging.basicConfig(level=settings.LOG_LEVEL)
        self.logger = logging.getLogger("AgentRouter")
        
        # Cliente explícito para GenAI SDK (Vertex AI Mode)
        self.client = Client(
            vertexai=settings.GOOGLE_GENAI_USE_VERTEXAI, 
            project=settings.PROJECT_ID, 
            location=settings.REGION,
            http_options={'api_version': 'v1', 'timeout': 900.0} 
        )
        
        # Prompt ligero para el triage inicial (Usando Single Quotes para seguridad)
        self.TRIAGE_PROMPT = '''
        Eres el Validador de People Analytics. Tu misión es RECOLECTAR dimensiones para consultas de datos O facilitar la EXPLORACIÓN del catálogo.

        ### MODOS DE ACTUACIÓN (PRIORIDAD DESCENDENTE):

        1. **MODO CONVERSACIONAL (Saludos/Ayuda):**
           - Si el usuario saluda ("hola", "buenos días") o pide ayuda general.
           - ACCIÓN: Responde amablemente y ofrece tu ayuda. **PROHIBIDO USAR TOOLS**.
           - Fin de la interacción.

        2. **MODO EXPLORACIÓN (Listado de Unidades):**
           - Si pide "ver las divisiones", usa `list_organizational_units(level='uo2')`.
           - Si pide "áreas de la división X", usa `list_organizational_units(level='uo3', parent_uo='X')`.
           - Entrega el listado en bullet points.

        3. **INTELIGENCIA DE MEMORIA (SLOTFILLING RÁPIDO):**
           - **ACCIÓN:** Usa `process_triage_step` para guardar lo que detectes.
           - **ESTADO:** Si "ESTADO DE MEMORIA" tiene el dato, NO lo pidas.
           
           - **MODO RECOLECCIÓN:**
             - Detecta dato -> `process_triage_step`.
             - Si faltan slots en el ESTADO, pídelos.

           - **MODO PREPARACIÓN (Solo cuando tengas los 3 Slots en MEMORIA):**
             - **NO VALIDES NADA EXTRAMENTE.** Asume que lo que dice el usuario existe.
             - Si tienes Periodo, Estructura y Forma -> Responde "PROCEED" INMEDIATAMENTE.
             - **YA NO PIDAS CONFIRMACIÓN EXPLICITA**. Si el usuario te dio los 3 datos, asume que quiere el reporte YA.
             
             - **REGLA DE HIERRO:** TÚ ERES TEXTO PURO. NUNCA intentes responder con datos, tablas o gráficos simulados. Si el usuario pide eso, REGISTRA LOS SLOTS y di "PROCEED".

        4. **BYPASS DE COMPLEJIDAD (Regla "Pasa la bola"):**
           - Si el usuario pide cosas complejas ("Evolución UO3", "Comparativa detallada", "Explicación profunda").
           - **COMPARATIVA DE SEGMENTOS:** Si el usuario pide comparar "Fuerza de Ventas vs Administrativos" (o similares):
             - **ACCIÓN:** No te detengas a elegir un segmento. Registra `structure='COMPARATIVA'`, `format='graph'` y responde "PROCEED" de inmediato.
           - **NO JUZGUES SI ES POSIBLE.** No es tu trabajo.
           - Tu trabajo es extraer lo básico y dar paso al EXPERTO.

        ### DICCIONARIO DE EQUIVALENCIAS (ZERO-SLOT):
        Para maximizar la agilidad, si detectas estas palabras, mapea el slot y di "PROCEED":
        - **ASUME `format='executive_report'` (Reporte Ejecutivo):**
          - "reporte ejecutivo", "informe ejecutivo", "executive report", "resumen ejecutivo", "dashboard ejecutivo".
          - **IMPORTANTE:** Si detectas reporte ejecutivo, establece `structure='TOTAL'` automáticamente.
        - **ASUME `format='table'` (Listado):** 
          - "lista", "listado", "relación", "tabla", "cuadro", "quiénes son", "detalle", "listar", "reporte", "nombres de".
        - **ASUME `format='graph'` (Evolución/Comparación):** 
          - "evolución", "tendencia", "mes a mes", "histórico", "gráfico", "curva", "línea", "comportamiento", "comparar", "comparativa", "versus", "vs", "diferencia entre".
        - **ASUME `format='kpi'` (Dato Puntual):** 
          - "cuánto es", "la cifra de", "el indicador", "el número", "valor", "dato".

        ### MAPA DE DIVISIONES (UO2): 
        Si el usuario nombra una, asume `structure` y nivel División:
        AUDITORIA INTERNA, DIVISION FINANZAS, DIVISION INVERSIONES, DIVISION LEGAL Y REGULACION, DIVISION MARKETING Y ESTRATEGIA, DIVISION RIESGOS, DIVISION SALUD, DIVISION SEGUROS EMPRESAS, DIVISION SEGUROS PERSONAS, DIVISION TALENTO, DIVISION TECNOLOGIA, DIVISION TRANSFORMACION.

        ### REGLAS DE ORO:
        - **VELOCIDAD PURA:** Tu trabajo es llenar el JSON y pasar al experto. No dudes. No valides.
        - **PROHIBIDO PREGUNTAR FORMATO:** Si el texto ya implica el formato (ej. "el listado"), **NO PREGUNTES**. Establece el slot y di "PROCEED".
        - **AGRUPACIONES:** Si el usuario dice "agrupado por X", establece `format='distribution'` si no especificó "tabla" o "listado". Pero si dijo "listado agrupado", `format='table'` manda.
        - **BYPASS:** Si el usuario dice "Analiza Finanzas 2025", llena los slots y lanza "PROCEED" en el mismo turno.
        - **PROHIBIDO GENERAR CÓDIGO:** NUNCA generes código Python de ejemplo. Solo llama a la herramienta `process_triage_step` y responde "PROCEED".
        - **COMPARATIVAS:** Si el usuario pide comparar métricas (ej. "total vs voluntaria vs involuntaria"), usa `structure='TOTAL'` y `format='graph'`. El agente experto se encargará de las métricas.
        
        ### EJEMPLOS DE AGILIDAD (FEW-SHOT):
        - **Usuario:** "Pásame la relación de cesados de Finanzas 2025"
          - *Acción:* Llama `process_triage_step(period='2025', structure='FINANZAS', format='table')` → Responde: "PROCEED".
        - **Usuario:** "¿Cuál es el cuadro de rotación de Marketing?"
          - *Acción:* Llama `process_triage_step(period='2025', structure='MARKETING', format='table')` → Responde: "PROCEED".
        - **Usuario:** "Evolución de rotación en 2024"
          - *Acción:* Llama `process_triage_step(period='2024', structure='TOTAL', format='graph')` → Responde: "PROCEED".
        - **Usuario:** "Gráfico comparativo de rotación total vs voluntaria vs involuntaria del 2025"
          - *Acción:* Llama `process_triage_step(period='2025', structure='TOTAL', format='graph')` → Responde: "PROCEED".
        - **Usuario:** "Reporte ejecutivo 2025"
          - *Acción:* Llama `process_triage_step(period='2025', structure='TOTAL', format='executive_report')` → Responde: "PROCEED".
        - **Usuario:** "Dame el informe ejecutivo de diciembre 2025"
          - *Acción:* Llama `process_triage_step(period='202512', structure='TOTAL', format='executive_report')` → Responde: "PROCEED".

        ### ALERTA CRÍTICA DE SISTEMA:
        **ESTRICAMENTE PROHIBIDO GENERAR BLOQUES DE CÓDIGO (```python ...```).**
        SI SIENTES LA NECESIDAD DE ESCRIBIR CÓDIGO, SIGNIFICA QUE DEBES LLAMAR A LA HERRAMIENTA `process_triage_step` EN SU LUGAR.
        TU SALIDA DEBE SER EXCLUSIVAMENTE LA LLAMADA A LA TOOL Y LUEGO LA PALABRA "PROCEED".
        '''

    def _track_and_log_rpm(self):
        """Mantiene una ventana móvil de 60 segundos para calcular RPM."""
        now = time.time()
        # Limpiar timestamps viejos (>60s)
        AgentRouter._request_timestamps = [t for t in AgentRouter._request_timestamps if now - t < 60]
        # Añadir actual
        AgentRouter._request_timestamps.append(now)
        rpm = len(AgentRouter._request_timestamps)
        self.logger.info(f"📊 [METRICS] Current RPM: {rpm} requests/min")
        return rpm

    def _clean_triage_response(self, text: str) -> str:
        """Limpia alucinaciones comunes de código en el triage."""
        if not text: return ""
        
        # 1. Eliminar bloques de código markdown
        clean = re.sub(r'```(?:python|json)?(.*?)```', r'\1', text, flags=re.DOTALL)
        
        # 2. Eliminar intentos de print()
        clean = re.sub(r'print\(.*?\)', '', clean, flags=re.DOTALL)
        
        # 3. Eliminar llamadas a API explícitas en texto (alucinación frecuente)
        clean = re.sub(r'default_api\.process_triage_step\(.*?\)', '', clean)
        
        return clean.strip()

    async def route(self, message: str, session_id: str = "default", profile: str = "EJECUTIVO") -> str:
        """
        Ejecuta la consulta a través de un Runner configurado para el perfil del usuario.
        """
        user_id = "default_user"
        app_name = "PeopleAnalyticsApp"

        # 1. Obtener agente especializado para el perfil
        specialized_agent = get_hr_agent(profile=profile)

        # Asegurar variables de entorno para inicialización implícita del cliente GenAI de ADK
        settings = get_settings()
        if settings.GOOGLE_GENAI_USE_VERTEXAI:
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
            os.environ["GOOGLE_CLOUD_PROJECT"] = settings.PROJECT_ID
            os.environ["GOOGLE_CLOUD_LOCATION"] = settings.REGION
        else:
             # Ensure we don't force Vertex if configured to False
             if "GOOGLE_GENAI_USE_VERTEXAI" in os.environ:
                 del os.environ["GOOGLE_GENAI_USE_VERTEXAI"]

        # 3. Preparar mensaje
        if profile:
            instruction_prefix = f"[INSTRUCCIÓN DE PERFIL: Responde asumiendo que el usuario es '{profile}'.]\n\n"
            full_message = instruction_prefix + message
        else:
            full_message = message

        # 0. TRIAGE INICIAL (Fast turn)
        # Evaluamos si vale la pena encender la maquinaria de herramientas
        
        # --- OPTIMIZACIÓN ZERO-LATENCY: Bypassing LLM para saludos triviales ---
        clean_msg = message.lower().strip()
        greetings = ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "qué tal", "que tal", "hola!"]
        if clean_msg in greetings or (len(clean_msg) < 15 and "hola" in clean_msg):
             self.logger.info("[ROUTER] Fast-Path detection: Greeting.")
             responses = [
                 "¡Hola! 👋 ¿En qué puedo ayudarte hoy con People Analytics?",
                 "¡Hola! Estoy listo para ayudarte a explorar datos o realizar análisis.",
                 "¡Buenas! ¿Qué información necesitas consultar hoy?"
             ]
             return random.choice(responses)
        # -----------------------------------------------------------------------

        # IMPORTANTE: Incluimos breve historial para evitar repeticiones (Context-Aware Triage)
        try:
            t_start_session = time.time()
            session = await self.session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
            self.logger.info(f"[ROUTER] Session fetch time: {time.time() - t_start_session:.4f}s")
            
            # --- GESTIÓN DE ESTADO (MEMORY SLOTS) ---
            triage_slots = {}
            if session:
                triage_slots = session.state.get("triage_slots", {})

            # --- HERRAMIENTA UNIFICADA DE BAJA LATENCIA ---
            def process_triage_step(
                period: str = None, 
                structure: str = None, 
                format: str = None,
                reset_memory: bool = False
            ):
                """
                ACCIÓN ATÓMICA: 
                1. Actualiza la memoria con lo nuevo.
                2. Valida automáticamente lo recibido (Año/Estructura).
                3. Devuelve estado actual y validaciones.
                """
                # 0. Reset si se solicita (cambio de tema)
                if reset_memory:
                    triage_slots.clear()
                    
                # 1. Actualizar Memoria
                if period: triage_slots["period"] = period
                if structure: triage_slots["structure"] = structure
                if format: triage_slots["format"] = format
                
                # 2. Validación "Dummy" (Ultrarrápida)
                # Ya NO consultamos BigQuery. Asumimos validez y dejamos que el experto (HR Agent) falle si es necesario.
                validation_log = []
                
                # Simple heurística de texto para evitar basura obvia
                cur_struct = triage_slots.get("structure")
                if cur_struct:
                    triage_slots["structure_valid"] = True # Fe ciega por velocidad

                cur_period = triage_slots.get("period")
                if cur_period:
                    triage_slots["period_valid"] = True

                return {
                    "memory_updated": triage_slots,
                    "validation_alerts": [], # Sin alertas de base de datos
                    "status": "Ready to Proceed" if triage_slots.get("period") and triage_slots.get("structure") and triage_slots.get("format") else "Missing Slots"
                }

            # ----------------------------------------------
            
            triage_contents = []
            if session and session.events:
                # Tomamos los últimos 150 eventos para garantizar contexto completo
                # NOTA: 10 eventos a veces se quedan cortos si hay mucha interacción 'small talk' previa.
                for ev in session.events[-15:]:
                    try:
                        role = "user" if ev.author == "user" else "model"
                        text_val = ""
                        # Extraer texto de forma robusta sea dict o objeto
                        content = ev.content
                        
                        # Debug raw content type
                        # print(f"DEBUG EVENT: {type(content)} - {content}")
                        
                        if isinstance(content, dict):
                            if "parts" in content:
                                for p in content["parts"]:
                                    if "text" in p: text_val += p["text"]
                            elif "text" in content:
                                text_val = content["text"]
                        elif isinstance(content, str):
                            text_val = content
                        elif hasattr(content, "parts"): # Soporte directo objeto GenAI
                             for p in content.parts:
                                 if p.text: text_val += p.text

                        if text_val:
                            # Usar diccionarios puros 
                            triage_contents.append({"role": role, "parts": [{"text": text_val}]})
                    except Exception as e:
                        self.logger.error(f"Error parsing event history: {e}")
                        continue

            # Añadir el mensaje actual (limpio)
            triage_contents.append({"role": "user", "parts": [{"text": message}]})
            
            # Incorporar ESTADO y PERFIL en la instrucción del sistema
            triage_instr = f"[ESTADO DE MEMORIA ACTUAL: {triage_slots}]\n\n[PERFIL USUARIO: {profile}]\n\n" + self.TRIAGE_PROMPT

            t_start_llm = time.time()
            self._track_and_log_rpm() # Telemetría antes de llamar
            
            try:
                triage_response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=triage_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=triage_instr,
                        temperature=0.0,
                        tools=[process_triage_step], # SOLO herramientas lógicas, nada de I/O
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=False,
                            maximum_remote_calls=3 
                        )
                    )
                )
            except Exception as e:
                # Catch specific timeout/read errors that might be wrapped
                error_str = str(e).lower()
                if "timeout" in error_str or "readoperation" in error_str or "deadline" in error_str:
                    self.logger.warning(f"⚠️ [ROUTER] Triage timed out with AFC. Retrying WITHOUT tools (Pure Text Fallback). Error: {e}")
                    # FALLBACK: Intentar sin herramientas para desbloquear
                    triage_response = self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=triage_contents,
                        config=types.GenerateContentConfig(
                            system_instruction=triage_instr + "\n\n[NOTA: EL VALIDADOR FALLÓ. RESPONDE SOLO CON TEXTO Y 'PROCEED' SI ES POSIBLE.]",
                            temperature=0.0,
                            tools=[], # Sin tools
                        )
                    )
                else:
                    raise e
                    
            self.logger.info(f"[ROUTER] LLM Generation time: {time.time() - t_start_llm:.4f}s")
            
            # Obtener texto de forma ultra-robusta
            triage_text = ""
            if triage_response.candidates:
                for part in triage_response.candidates[0].content.parts:
                    if part.text:
                        triage_text += part.text
            
            # ---> NUEVA LÓGICA DE LIMPIEZA <---
            triage_text = self._clean_triage_response(triage_text)

            if triage_text and "PROCEED" not in triage_text:
                self.logger.info(f"[TRIAGE] Prompting for clarification: {triage_text[:50]}...")
                
                # PERSISTIR TURNO EN LA SESIÓN PARA NO PERDER CONTEXTO
                if not session:
                    session = await self.session_service.create_session(
                        app_name=app_name, user_id=user_id, session_id=session_id
                    )
                
                # ACTUALIZAR ESTADO EN LA SESIÓN
                session.state["triage_slots"] = triage_slots
                
                # Guardar el mensaje del usuario de forma limpia (sin prefijos de sistema)
                await self.session_service.append_event(session, Event(
                    author="user",
                    content={"parts": [{"text": message}]}
                ))
                # Guardar la respuesta del triaje
                await self.session_service.append_event(session, Event(
                    author="model",
                    content={"parts": [{"text": triage_text}]}
                ))
                
                return triage_text
        except Exception as e:
            self.logger.error(f"Triage failed: {e}. Falling back to full agent.")
            # self.logger.error(traceback.format_exc()) # Reduce noise
            pass

        # 2. Inicializar Runner dinámico (Maquinaria pesada)
        # Inyectamos el ESTADO del triaje directamente en el agente para evitar re-lectura de historial
        specialized_agent = get_hr_agent(profile=profile, context_state=triage_slots)
        
        runner = Runner(
            app_name=app_name,
            agent=specialized_agent,
            session_service=self.session_service
        )

        new_message = types.Content(parts=[types.Part(text=full_message)], role="user")
        
        # 4. Asegurar sesión (Confirmado Async)
        if not await self.session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id):
            await self.session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)

        max_retries = 3
        retry_delay = 5 # Aumentamos delay inicial por seguridad (era 2)
        
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
                
                t_run_start = time.time()
                t_last_event = t_run_start
                t_tool_start = 0

                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=new_message
                ):
                    now = time.time()
                    delta = now - t_last_event
                    t_last_event = now

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
                                self.logger.info(f"[PROFILER] 🤖 Model planned tool: {part.function_call.name} (Think time: {delta:.4f}s)")
                                # After a function call, a new call will follow to process the result
                                current_turn_counted = False
                                t_tool_start = time.time()

                            if part.function_response:
                                duration = time.time() - t_tool_start
                                self.logger.info(f"[PROFILER] 🛠️ Tool execution finished in {duration:.4f}s")
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
                
                # RESILIENCE BLOCK: Timeout/Network Error but Data was Generated
                elif "timeout" in error_msg.lower() or "readoperation" in error_msg.lower():
                    if last_tool_result and isinstance(last_tool_result, dict):
                         self.logger.warning(f"⚠️ [RESILIENCE] LLM Timeout ({error_msg}) but Tool Data was captured. Returning data to user.")
                         break # Break loop, code below will return last_tool_result
                    else:
                         self.logger.error(f"Runner failed with Timeout and no data: {e}")
                         raise e
                else:
                    self.logger.error(f"Runner failed: {e}")
                    # Validate if we have a valid package before raising
                    if last_tool_result and isinstance(last_tool_result, dict) and last_tool_result.get("response_type") == "visual_package":
                         self.logger.warning(f"⚠️ [RESILIENCE] Unknown Error ({error_msg}) but Tool Data captured. Returning data.")
                         break
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
