import logging
import json
import asyncio
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from dateutil.relativedelta import relativedelta

from app.ai.tools.universal_analyst import execute_semantic_query
from app.ai.tools.executive_insights import ReportInsightGenerator
from app.schemas.payloads import VisualDataPackage, TextBlock
from app.core.analytics.registry import DEFAULT_LISTING_COLUMNS

logger = logging.getLogger(__name__)

# --- PERIOD UTILITIES ---

def parse_period(periodo: str) -> Dict:
    periodo = periodo.strip()
    range_match = re.match(r'^(\d{6})-(\d{6})$', periodo)
    if range_match:
        start_str, end_str = range_match.groups()
        start_dt = datetime.strptime(start_str, "%Y%m")
        end_dt = datetime.strptime(end_str, "%Y%m")
        delta = relativedelta(end_dt, start_dt)
        months_diff = delta.years * 12 + delta.months + 1
        return {
            "granularity": "RANGE", "start": start_str, "end": end_str,
            "months_duration": months_diff, "original": periodo,
            "display": f"{start_dt.strftime('%b %Y')} - {end_dt.strftime('%b %Y')}"
        }
    if re.match(r'^\d{4}$', periodo):
        year = int(periodo)
        return {"granularity": "YEAR", "year": year, "original": periodo, "display": f"Año {year}"}
    quarter_match = re.match(r'^(\d{4})Q([1-4])$', periodo, re.IGNORECASE)
    if quarter_match:
        year = int(quarter_match.group(1)); quarter = int(quarter_match.group(2))
        return {"granularity": "QUARTER", "year": year, "quarter": quarter, "original": periodo, "display": f"Q{quarter} {year}"}
    if re.match(r'^\d{6}$', periodo):
        year = int(periodo[:4]); month = int(periodo[4:6])
        if 1 <= month <= 12:
            month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            return {"granularity": "MONTH", "year": year, "month": month, "original": periodo, "display": f"{month_names[month-1]} {year}"}
    raise ValueError(f"Invalid period format '{periodo}'.")

def get_previous_period(periodo: str) -> str:
    parsed = parse_period(periodo)
    if parsed["granularity"] == "RANGE":
        duration = parsed["months_duration"]
        current_start = datetime.strptime(parsed["start"], "%Y%m")
        prev_start = current_start - relativedelta(months=duration)
        prev_end = prev_start + relativedelta(months=duration - 1)
        return f"{prev_start.strftime('%Y%m')}-{prev_end.strftime('%Y%m')}"
    elif parsed["granularity"] == "YEAR": return str(parsed["year"] - 1)
    elif parsed["granularity"] == "QUARTER":
        if parsed["quarter"] == 1: return f"{parsed['year'] - 1}Q4"
        return f"{parsed['year']}Q{parsed['quarter'] - 1}"
    elif parsed["granularity"] == "MONTH":
        prev_date = datetime(parsed["year"], parsed["month"], 1) - relativedelta(months=1)
        return prev_date.strftime("%Y%m")
    return periodo

def get_period_filters(parsed: Dict) -> List[Dict]:
    if parsed["granularity"] == "RANGE":
        return [{"dimension": "periodo", "operator": ">=", "value": parsed["start"]}, {"dimension": "periodo", "operator": "<=", "value": parsed["end"]}]
    if parsed["granularity"] == "YEAR": return [{"dimension": "anio", "value": parsed["year"]}]
    if parsed["granularity"] == "QUARTER": return [{"dimension": "anio", "value": parsed["year"]}, {"dimension": "trimestre", "value": parsed["quarter"]}]
    if parsed["granularity"] == "MONTH": return [{"dimension": "periodo", "value": parsed["original"]}]
    return []

# --- CORE LOGIC ---

from app.services.report_snapshot_service import ReportSnapshotService

# --- SEMANTIC INTERPRETER ---

from app.core.config.config import get_settings
from google.genai import types, Client
from google.genai.errors import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class SemanticInterpreter:
    """Translates NL questions into structured cube_queries using Gemini with Retry Logic."""
    def __init__(self):
        from app.ai.agents.hr_agent import HR_PROMPT_SEMANTIC
        self.settings = get_settings()
        self.client = Client(
            vertexai=self.settings.GOOGLE_GENAI_USE_VERTEXAI,
            project=self.settings.PROJECT_ID,
            location=self.settings.REGION
        )
        self.model_name = self.settings.MODEL_NAME or "gemini-2.0-flash-exp"
        self.instruction = HR_PROMPT_SEMANTIC + "\n\nCRÍTICO: Retorna UNICAMENTE el JSON de los argumentos para execute_semantic_query."

    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(10),  # High retry count for batch processing
        wait=wait_exponential(multiplier=4, min=10, max=120),  # Aggressive backoff: 10s, 20s, 40s...
        reraise=True
    )
    def _generate_with_retry(self, prompt: str):
        """Executes generation with backoff policy for 429 errors."""
        logger.info("🔄 Calling Gemini for translation...")
        return self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

    def translate(self, question: str) -> Dict:
        """Translates a question to a semantic query dict. RAISES on error for Fail-Fast."""
        # Inject system instruction into the prompt for context-aware translation
        prompt = f"{self.instruction}\n\nUSER QUESTION: '{question}'\n\nJSON:"
        # Uses the retrying method. If it fails after retries, it triggers RetryError (bubbling up).
        response = self._generate_with_retry(prompt)
        return json.loads(response.text)

# --- CORE LOGIC ---

def _get_report_prompts(parsed: Dict, prev_p: str, scope: str) -> Dict[str, str]:
    """
    Generates dynamic, context-aware prompts for the Executive Report based on granularity.
    
    Args:
        parsed: Result from parse_period (contains 'granularity', 'year', 'display', etc.)
        prev_p: Display string for the previous period (e.g., '202411' or '2024').
        scope: Organizational scope (e.g., 'Global', 'DIVISION TALENTO').
    
    Returns:
        Dict[str, str]: The 7-block manifest of natural language questions.
    """
    is_year = parsed["granularity"] == "YEAR"
    year = parsed["year"]
    
    if is_year:
        return {
            "headline_current": f"Calcula la tasa de rotación anualizada, ceses totales y headcount promedio ACUMULADO para TODO EL AÑO {year} en {scope}. (No te limites a un solo mes)",
            "headline_previous": f"Calcula la tasa de rotación anualizada, ceses totales y headcount promedio ACUMULADO para el AÑO ANTERIOR {year - 1} en {scope}",
            "annual_stats": f"Dame la tasa de rotación y ceses totales ACUMULADOS (YTD) para el AÑO {year} en {scope}",
            "segmentation": f"Compara la tasa de rotación y ceses por grupo_segmento (Administrativo vs Fuerza de Ventas) ACUMULADO ANUAL {year} en {scope}",
            "voluntary": f"Muestra la distribución de tasa de rotación voluntaria e involuntaria ACUMULADA del año {year} en {scope}",
            "talent": f"Lista los colaboradores HiPo o HiPer que han cesado durante TODO EL AÑO {year} en {scope}",
            "trend": f"Muestra la evolución MENSUAL de la tasa de rotación para cada mes del año {year} en {scope}"
        }
    else:
        display = parsed['display']
        return {
            "headline_current": f"Calcula la tasa de rotación, ceses totales y headcount promedio para el MES de {display} en {scope}",
            "headline_previous": f"Calcula la tasa de rotación, ceses totales y headcount promedio para el MES ANTERIOR ({prev_p}) en {scope}",
            "annual_stats": f"Dame la tasa de rotación y ceses totales acumulados (YTD) para el año {year} hasta {display} en {scope}",
            "segmentation": f"Compara la tasa de rotación y ceses por grupo_segmento (Administrativo vs Fuerza de Ventas) para el MES de {display} en {scope}",
            "voluntary": f"Muestra la distribución de tasa de rotación voluntaria e involuntaria para el MES de {display} en {scope}",
            "talent": f"Lista los colaboradores HiPo o HiPer que han cesado en el MES de {display} en {scope}",
            "trend": f"Muestra la evolución MENSUAL de la tasa de rotación para el año {year} (Enero a Diciembre) en {scope}"
        }

async def generate_executive_report(
    periodo_anomes: str, 
    uo2_filter: Optional[str] = None, 
    sections: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generates a holistic Executive Report for a specific period and optional scope.
    
    Args:
        periodo_anomes: Target period. 
            - Use 'YYYY' (e.g., '2025') for FULL YEAR reports.
            - Use 'YYYYMM' (e.g., '202511') for MONTHLY reports.
        uo2_filter: Optional Division/Unit filter (e.g., 'DIVISION TALENTO'). Defaults to 'Global'.
    """
    try:
        parsed = parse_period(periodo_anomes)
        prev_p = get_previous_period(periodo_anomes)
        scope = uo2_filter or "Global"
        
        # Determine Context Label for the Report Title
        is_year = parsed["granularity"] == "YEAR"
        label_period = f"AÑO {parsed['year']}" if is_year else parsed['display']
        ctx_label = f"{label_period} | {scope}"
        
        # Initialize Services
        interpreter = SemanticInterpreter()
        snapshot_svc = ReportSnapshotService()
        report_id = snapshot_svc.create_snapshot(periodo_anomes, scope)
        logger.info(f"🚀 Started Report 2.0: {report_id} (Granularity: {parsed['granularity']})")

        # 1. Define Natural Language Questions (Dynamic Manifest via Helper)
        questions = _get_report_prompts(parsed, prev_p, scope)

        # 2. Gather Data (Strict Sequential with Fail-Fast)
        results = {}
        for key, text in questions.items():
            logger.info(f"🧠 Interpreting ({key}): {text}")
            
            # CRITICAL: Fail-Fast Logic
            # If translate fails (throws RetryError after 10 attempts), 
            # the entire process stops and returns the error to the user.
            spec = interpreter.translate(text)
            
            if spec:
                # Add metadata to help the Semantic Engine generate better titles/descriptions
                if "metadata" not in spec: spec["metadata"] = {}
                spec["metadata"]["report_context"] = ctx_label
                spec["metadata"]["block_key"] = key
                
                results[key] = execute_semantic_query(
                    intent=spec.get("intent", "SNAPSHOT"),
                    cube_query=spec.get("cube_query", {}),
                    metadata=spec.get("metadata", {})
                )
            else:
                 # Should technically be unreachable if translate raises, but strictly handling empty return just in case
                 raise ValueError("Semantic translation returned empty specification.")

        # 3. Store Snapshot in Firestore
        snapshot_svc.update_snapshot(report_id, results)

        # 4. Generate Holistic Narratives
        logger.info(f"🎨 Generating holistic narratives for {report_id}...")
        ai_gen = ReportInsightGenerator()
        ai_narratives = ai_gen.generate_report_narratives(results, ctx_label)
        snapshot_svc.save_narratives(report_id, ai_narratives)

        # 5. Assemble Visual Package
        blocks = [
            {"type": "text", "payload": f"Reporte Ejecutivo: {ctx_label}", "variant": "h2"},
            {"type": "text", "payload": ai_narratives.get("critical_insight", "Generando resumen..."), "variant": "insight"}
        ]
        
        # Headline KPIs
        blocks.extend(results["headline_current"].get("content", []))
        
        # Segmentation
        blocks.append({"type": "text", "payload": "Análisis por Segmento", "variant": "h3"})
        blocks.extend(results["segmentation"].get("content", []))
        blocks.append({"type": "text", "payload": ai_narratives.get("segmentation", ""), "variant": "standard"})
        
        # Voluntary
        blocks.append({"type": "text", "payload": "Distribución de Rotación Voluntaria", "variant": "h3"})
        blocks.extend(results["voluntary"].get("content", []))
        blocks.append({"type": "text", "payload": ai_narratives.get("voluntary_trend", ""), "variant": "standard"})

        # Talent
        if results["talent"].get("content"):
            blocks.append({"type": "text", "payload": "Fuga de Talento Crítico", "variant": "h3"})
            blocks.extend(results["talent"].get("content", []))
            blocks.append({"type": "text", "payload": ai_narratives.get("talent_leakage", ""), "variant": "insight"})
            
        # Trend
        blocks.append({"type": "text", "payload": "Evolución de Rotación", "variant": "h3"})
        blocks.extend(results["trend"].get("content", []))

        # Strategic Conclusion
        blocks.append({"type": "text", "payload": "Conclusión Estratégica", "variant": "h3"})
        blocks.append({"type": "text", "payload": ai_narratives.get("strategic_conclusion", ""), "variant": "standard"})

        # Recommendations (New Expert Block)
        recs = ai_narratives.get("recommendations")
        if recs:
            if isinstance(recs, list):
                recs_text = "\n".join([f"• {r}" for r in recs])
            else:
                recs_text = str(recs)
            
            blocks.append({"type": "text", "payload": "Recomendaciones Tácticas (AI Expert)", "variant": "h3"})
            blocks.append({"type": "text", "payload": recs_text, "variant": "insight"})

        return _sanitize_output({
            "response_type": "visual_package",
            "summary": f"Reporte Ejecutivo de Rotación - ID: {report_id}",
            "content": blocks,
            "metadata": {"report_id": report_id}
        })

    except Exception as e:
        logger.error(f"Error in Orchestrator 2.0: {e}", exc_info=True)
        return {"response_type": "error", "summary": f"Error: {str(e)}", "content": []}

def _sanitize_output(payload: Dict) -> Dict:
    # Recursively clean payload for JSON safety
    def clean(obj):
        if isinstance(obj, list): return [clean(x) for x in obj]
        if isinstance(obj, dict): return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)): return None
        return obj
    
    import math
    return clean(payload)
