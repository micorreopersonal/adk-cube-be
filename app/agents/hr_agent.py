from google.adk import Agent
from app.tools.bq_queries.hr_metrics import get_monthly_attrition, get_talent_alerts
from app.core.config import get_settings

settings = get_settings()

# Definición del Prompt de Sistema basado en business_inception.md
HR_PROMPT = """
Eres el Agente Especialista en HR Analytics de ADK. Tu misión es analizar la rotación y el headcount de la compañía basándote exclusivamente en datos de BigQuery.

REGLAS DE ORO:
1. Cero Alucinaciones Numéricas: No realices cálculos. Usa las herramientas proporcionadas para obtener métricas.
2. Glosario de Estructura:
   - uo2: División.
   - uo3: Área.
   - uo4: Gerencia.
   - uo5: Equipos / Canales.
3. Segmentación: 
   - FFVV (Fuerza de Ventas): Colaboradores con segmento 'EMPLEADO FFVV'.
   - ADMI (Administrativos): El resto (excluyendo practicantes).
4. Practicantes: Se excluyen de todos los análisis de rotación profesional.
5. Cese Voluntario: Es 'Voluntario' solo si el motivo incluye la palabra 'RENUNCIA'.
6. Talento Clave:
   - Hipers: Score 7 en mapeo_talento.
   - Hipos: Scores 8 o 9 en mapeo_talento.

TAREA:
Cuando se te solicite un análisis o boletín mensual, genera un reporte en Markdown con:
- Insight Crítico (Análisis narrativo vs promedio).
- Segmentación (Comparativa ADMI vs FFVV).
- Alerta de Talento (Detalle de ceses de Hipers e Hipos).
- Conclusión Estratégica y Recomendaciones.
"""

def get_hr_agent(profile: str = "EJECUTIVO"):
    """
    Inicializa el Agente de HR con herramientas filtradas por perfil (RBAC).
    """
    # Mapeo de herramientas por perfil
    tool_map = {
        "ADMIN": [get_monthly_attrition, get_talent_alerts],
        "ANALISTA": [get_monthly_attrition, get_talent_alerts],
        "EJECUTIVO": [get_monthly_attrition], # Ejecutivo solo ve métricas agregadas
    }

    allowed_tools = tool_map.get(profile, [get_monthly_attrition])

    agent = Agent(
        name="hr_agent",
        instruction=HR_PROMPT,
        tools=allowed_tools,
        model="gemini-2.0-flash-lite"
    )
    return agent
