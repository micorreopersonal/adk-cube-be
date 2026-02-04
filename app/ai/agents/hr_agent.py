from datetime import datetime
from google.adk import Agent
from google.adk.models import Gemini
from app.core.config import get_settings
from app.ai.tools.universal_analyst import execute_semantic_query
from app.core.analytics.registry import METRICS_REGISTRY, DIMENSIONS_REGISTRY

settings = get_settings()

def get_vertex_model():
    return Gemini(
        project_id=settings.PROJECT_ID,
        location=settings.REGION,
        model_name=settings.MODEL_NAME,
        max_output_tokens=2048,
        temperature=0.0
    )

# Generar listas dinámicas para el Prompt
metrics_keys = list(METRICS_REGISTRY.keys())
dims_keys = list(DIMENSIONS_REGISTRY.keys())

METRICS_LIST = "\n".join([f"- {k}: {v.get('label', k)}" for k, v in METRICS_REGISTRY.items()])
DIMS_LIST = ", ".join(dims_keys)

# Obtener valores reales de divisiones para el prompt (Zero-Shot Accuracy)
try:
    from app.services.bigquery import get_bq_service
    bq = get_bq_service()
    CUBE_SOURCE = f"`{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`"
    divisions_df = bq.execute_query(f"SELECT DISTINCT uo2 FROM {CUBE_SOURCE} WHERE uo2 IS NOT NULL ORDER BY 1")
    REAL_DIVISIONS = ", ".join(divisions_df['uo2'].tolist())
except Exception as e:
    REAL_DIVISIONS = "DIVISION TALENTO, DIVISION SEGUROS PERSONAS, DIVISION FINANZAS, DIVISION RIESGOS"

# Contexto Dinámico de Tiempo
NOW = datetime(2025, 12, 1) # Simulación de producción
CURRENT_DATE_STR = NOW.strftime("%Y-%m-%d")
CURRENT_MONTH = NOW.month
CURRENT_YEAR = NOW.year
CURRENT_QUARTER = (NOW.month - 1) // 3 + 1

HR_PROMPT_SEMANTIC = f'''
Eres el Nexus AI Architect.
Tu misión es traducir PREGUNTAS DE NEGOCIO en SOLICITUDES ANALÍTICAS ESTRUCTURADAS (JSON).

### CONTEXTO TEMPORAL ACTUAL:
- Fecha: {CURRENT_DATE_STR} | Mes: {CURRENT_MONTH} | Año: {CURRENT_YEAR} | Q: {CURRENT_QUARTER}

### REGISTRY:
METRICS:
{METRICS_LIST}

DIMENSIONS:
[{DIMS_LIST}]

### DATOS MAESTROS (Valores Reales para Filtros):
VALORES EN uo2 (Divisiones): {REAL_DIVISIONS}

### REGLAS DE TRADUCCIÓN CRÍTICAS:
1. **Mapeo de "Personas"**: 
   - SIEMPRE que digan "División de Personas" o "Seguros de Personas", usa `uo2` = "DIVISION SEGUROS PERSONAS".
   - SOLO si dicen "Recursos Humanos", "RRHH" o "Talento", usa `uo2` = "DIVISION TALENTO".

2. **Llamada a Herramienta (`execute_semantic_query`)**:
   - Debes pasar los argumentos de forma estructurada según la firma:
     - `intent`: "TREND", "COMPARISON" o "SNAPSHOT".
     - `cube_query`: {{ "metrics": [...], "dimensions": [...], "filters": [...] }}
     - `metadata`: {{ "requested_viz": "...", "title_suggestion": "..." }}
   - **IMPORTANTE**: `filters` es una LISTA de objetos `{{ "dimension": "...", "value": ... }}`. NO uses diccionarios planos.

3. **Intentos (`intent`)**:
   - `TREND`: Para evoluciones temporales (mes a mes).
   - `COMPARISON`: Para comparar dimensiones o periodos.
   - `LISTING`: **ÚSALO SIEMPE** que pidan "lista", "listado", "detalle", "quiénes son", "relación de personas", "nombres".
     - **REGLA DE ORO (Contexto Rotación):** Si piden "listado de personas" o "colaboradores" SIN especificar estado, **ASUME `estado='Cesado'`**. Solo usa `Activo` si lo piden explícitamente.
     - **Dimensiones Obligatorias**: `periodo`, `uo2`, `uo3`, `nombre_completo`, `posicion`, `segmento`, `talento`, `per_anual`, `motivo_cese`.
     - **Métricas**: Ninguna.
   - `SNAPSHOT`: Para una foto única de métricas (KPIs).

4. **Visualización (`requested_viz`)**:
   - Usa `TABLE` para cualquier pedido de "lista" o "detalle".
   - Usa `LINE_CHART` para tendencias.
   - Usa `BAR_CHART` para comparaciones.
   - Usa `KPI_ROW` solo si piden "cuánto" o "el total".

### EJEMPLO DE LISTA (Correcto):
Tool: execute_semantic_query
Arguments:
{{
  "intent": "LISTING",
  "cube_query": {{
    "metrics": [],
    "dimensions": ["periodo", "uo2", "uo3", "nombre_completo", "posicion", "segmento", "talento", "per_anual", "motivo_cese", "fecha_cese"],
    "filters": [
      {{"dimension": "anio", "value": 2025}},
      {{"dimension": "mes", "value": 12}},
      {{"dimension": "uo2", "value": "DIVISION SEGUROS PERSONAS"}},
      {{"dimension": "estado", "value": "Cesado"}}
    ]
  }},
  "metadata": {{ 
    "requested_viz": "TABLE", 
    "title_suggestion": "Listado Detallado de Ceses - Dic 2025" 
  }}
}}

### REGLAS TEMPORALES CRÍTICAS:
- **"Último mes cerrado"** o **"último período"**: Usa el valor especial `"MAX"` para la dimensión `periodo`. 
  - Ejemplo: `{{"dimension": "periodo", "value": "MAX"}}`
  - El sistema automáticamente consultará el `MAX(periodo)` de la tabla (el último mes con datos).
- **TRANSPARENCIA OBLIGATORIA**: El `title_suggestion` DEBE incluir "Último Mes Cerrado" para que el usuario sepa que es dinámico.
  - Ejemplo: "Ceses - Último Mes Cerrado"

### REGLAS ADICIONALES:
Tool: execute_semantic_query
Arguments:
{{
  "intent": "TREND",
  "cube_query": {{
    "metrics": ["tasa_rotacion"],
    "dimensions": ["mes", "uo3"],
    "filters": [
      {{"dimension": "anio", "value": 2025}},
      {{"dimension": "uo2", "value": "DIVISION SEGUROS PERSONAS"}}
    ]
  }}
}}

### IMPORTANTE:
- Responde SOLO con la llamada a la herramienta.
- NO generes SQL.
'''

def get_hr_agent(profile: str = "EJECUTIVO", context_state: dict = None):
    """Retorna la configuración del Agente HR Semántico (v2.1 Nexus)."""
    
    final_instruction = HR_PROMPT_SEMANTIC
    if context_state:
        context_str = "\n\n### ESTADO DETERMINADO POR TRIAJE (Prioridad Alta):\n"
        for k, v in context_state.items():
            context_str += f"- {k.upper()}: {v}\n"
        context_str += "\nSI EL FORMATO ES 'TABLE', DEBES USAR INTENT='LISTING' Y REQUESTED_VIZ='TABLE'.\n"
        final_instruction = context_str + HR_PROMPT_SEMANTIC

    return Agent(
        name="HR_Semantic_Agent",
        instruction=final_instruction,
        model=get_vertex_model(),
        tools=[execute_semantic_query]
    )
