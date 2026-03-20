import logging
import math
import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Any, List, Optional
from dateutil.relativedelta import relativedelta

from app.ai.tools.universal_analyst import execute_semantic_query
from app.ai.tools.executive_insights import ReportInsightGenerator
from app.services.report_snapshot_service import ReportSnapshotService

logger = logging.getLogger(__name__)

# Thread pool for parallel BQ execution (shared across calls)
_executor = ThreadPoolExecutor(max_workers=7)

# All valid section keys for the executive report
ALL_SECTIONS = [
    "headline_current", "headline_previous", "annual_stats",
    "segmentation", "voluntary", "talent", "trend"
]

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


# --- DIRECT QUERY BUILDERS (replaces SemanticInterpreter + Gemini calls) ---

def _build_scope_filters(uo2_filter: Optional[str]) -> List[Dict]:
    """Returns uo2 filter list if scope is not Global."""
    if uo2_filter:
        return [{"dimension": "uo2", "value": uo2_filter}]
    return []

def _build_report_blocks(parsed: Dict, prev_periodo: str, uo2_filter: Optional[str]) -> Dict[str, Dict]:
    """
    Builds deterministic cube_query specs for each report block.
    Eliminates the Gemini NL→JSON translation hop entirely.

    Returns:
        Dict[block_key, {intent, cube_query, metadata}]
    """
    granularity = parsed["granularity"]
    year = parsed["year"]
    scope_filters = _build_scope_filters(uo2_filter)

    # Period filters for current and previous
    current_filters = get_period_filters(parsed)
    prev_parsed = parse_period(prev_periodo)
    prev_filters = get_period_filters(prev_parsed)

    blocks = {}

    # --- HEADLINE CURRENT ---
    if granularity == "YEAR":
        blocks["headline_current"] = {
            "intent": "SNAPSHOT",
            "cube_query": {
                "metrics": ["tasa_rotacion_anual", "ceses_acumulado", "personal_activo_total"],
                "dimensions": [],
                "filters": [{"dimension": "anio", "value": year}] + scope_filters,
            },
            "metadata": {"requested_viz": "KPI_ROW", "title_suggestion": f"KPIs Rotación Año {year}"}
        }
    elif granularity == "QUARTER":
        blocks["headline_current"] = {
            "intent": "SNAPSHOT",
            "cube_query": {
                "metrics": ["tasa_rotacion_mensual", "ceses_totales", "personal_activo_total"],
                "dimensions": [],
                "filters": [
                    {"dimension": "anio", "value": year},
                    {"dimension": "trimestre", "value": parsed["quarter"]}
                ] + scope_filters,
            },
            "metadata": {"requested_viz": "KPI_ROW", "title_suggestion": f"KPIs Rotación {parsed['display']}"}
        }
    else:  # MONTH or RANGE
        blocks["headline_current"] = {
            "intent": "SNAPSHOT",
            "cube_query": {
                "metrics": ["tasa_rotacion_mensual", "ceses_totales", "personal_activo_total"],
                "dimensions": [],
                "filters": current_filters + scope_filters,
            },
            "metadata": {"requested_viz": "KPI_ROW", "title_suggestion": f"KPIs Rotación {parsed['display']}"}
        }

    # --- HEADLINE PREVIOUS (for comparison) ---
    if granularity == "YEAR":
        blocks["headline_previous"] = {
            "intent": "SNAPSHOT",
            "cube_query": {
                "metrics": ["tasa_rotacion_anual", "ceses_acumulado", "personal_activo_total"],
                "dimensions": [],
                "filters": [{"dimension": "anio", "value": year - 1}] + scope_filters,
            },
            "metadata": {"requested_viz": "KPI_ROW", "title_suggestion": f"KPIs Periodo Anterior ({year - 1})"}
        }
    elif granularity == "QUARTER":
        prev_q_parsed = parse_period(prev_periodo)
        blocks["headline_previous"] = {
            "intent": "SNAPSHOT",
            "cube_query": {
                "metrics": ["tasa_rotacion_mensual", "ceses_totales", "personal_activo_total"],
                "dimensions": [],
                "filters": get_period_filters(prev_q_parsed) + scope_filters,
            },
            "metadata": {"requested_viz": "KPI_ROW", "title_suggestion": f"KPIs Periodo Anterior ({prev_periodo})"}
        }
    else:
        blocks["headline_previous"] = {
            "intent": "SNAPSHOT",
            "cube_query": {
                "metrics": ["tasa_rotacion_mensual", "ceses_totales", "personal_activo_total"],
                "dimensions": [],
                "filters": prev_filters + scope_filters,
            },
            "metadata": {"requested_viz": "KPI_ROW", "title_suggestion": f"KPIs Periodo Anterior ({prev_periodo})"}
        }

    # --- ANNUAL STATS (YTD) ---
    blocks["annual_stats"] = {
        "intent": "SNAPSHOT",
        "cube_query": {
            "metrics": ["tasa_rotacion_anual", "ceses_acumulado"],
            "dimensions": [],
            "filters": [{"dimension": "anio", "value": year}] + scope_filters,
        },
        "metadata": {"requested_viz": "KPI_ROW", "title_suggestion": f"Acumulado Anual {year}"}
    }

    # --- SEGMENTATION (FFVV vs Admin) ---
    if granularity == "YEAR":
        seg_filters = [{"dimension": "anio", "value": year}] + scope_filters
        seg_metrics = ["tasa_rotacion_anual", "ceses_acumulado"]
    elif granularity == "QUARTER":
        seg_filters = [
            {"dimension": "anio", "value": year},
            {"dimension": "trimestre", "value": parsed["quarter"]}
        ] + scope_filters
        seg_metrics = ["tasa_rotacion_mensual", "ceses_totales"]
    else:
        seg_filters = current_filters + scope_filters
        seg_metrics = ["tasa_rotacion_mensual", "ceses_totales"]

    blocks["segmentation"] = {
        "intent": "COMPARISON",
        "cube_query": {
            "metrics": seg_metrics,
            "dimensions": ["grupo_segmento"],
            "filters": seg_filters,
        },
        "metadata": {"requested_viz": "BAR_CHART", "title_suggestion": "Rotación por Segmento (FFVV vs Admin)"}
    }

    # --- VOLUNTARY vs INVOLUNTARY ---
    if granularity == "YEAR":
        vol_filters = [{"dimension": "anio", "value": year}] + scope_filters
        vol_metrics = ["tasa_rotacion_anual_voluntaria", "tasa_rotacion_anual_involuntaria"]
    elif granularity == "QUARTER":
        vol_filters = [
            {"dimension": "anio", "value": year},
            {"dimension": "trimestre", "value": parsed["quarter"]}
        ] + scope_filters
        vol_metrics = ["tasa_rotacion_mensual_voluntaria", "tasa_rotacion_mensual_involuntaria"]
    else:
        vol_filters = current_filters + scope_filters
        vol_metrics = ["tasa_rotacion_mensual_voluntaria", "tasa_rotacion_mensual_involuntaria"]

    blocks["voluntary"] = {
        "intent": "SNAPSHOT",
        "cube_query": {
            "metrics": vol_metrics,
            "dimensions": [],
            "filters": vol_filters,
        },
        "metadata": {"requested_viz": "KPI_ROW", "title_suggestion": "Distribución Voluntaria vs Involuntaria"}
    }

    # --- TALENT LEAKAGE (HiPo/HiPer) ---
    talent_filters = current_filters if granularity != "YEAR" else [{"dimension": "anio", "value": year}]
    if granularity == "QUARTER":
        talent_filters = [
            {"dimension": "anio", "value": year},
            {"dimension": "trimestre", "value": parsed["quarter"]}
        ]

    blocks["talent"] = {
        "intent": "LISTING",
        "cube_query": {
            "metrics": [],
            "dimensions": ["periodo", "uo2", "nombre_completo", "posicion", "segmento", "grupo_talento", "motivo_cese"],
            "filters": talent_filters + scope_filters + [
                {"dimension": "estado", "value": "Cesado"},
                {"dimension": "grupo_talento", "operator": "IN", "value": ["HiPo", "HiPer"]}
            ],
        },
        "metadata": {"requested_viz": "TABLE", "title_suggestion": "Fuga de Talento Crítico (HiPo/HiPer)"}
    }

    # --- TREND (Monthly evolution) ---
    blocks["trend"] = {
        "intent": "TREND",
        "cube_query": {
            "metrics": ["tasa_rotacion_mensual"],
            "dimensions": ["mes"],
            "filters": [{"dimension": "anio", "value": year}] + scope_filters,
        },
        "metadata": {"requested_viz": "LINE_CHART", "title_suggestion": f"Evolución Mensual de Rotación {year}"}
    }

    return blocks


# --- PARALLEL EXECUTION ENGINE ---

def _execute_block(key: str, spec: Dict, ctx_label: str) -> tuple:
    """
    Executes a single report block via execute_semantic_query.
    Returns (key, result_dict) on success or (key, error_placeholder) on failure.
    """
    try:
        # Inject report context into metadata
        metadata = spec.get("metadata", {})
        metadata["report_context"] = ctx_label
        metadata["block_key"] = key

        result = execute_semantic_query(
            intent=spec["intent"],
            cube_query=spec["cube_query"],
            metadata=metadata
        )
        logger.info(f"  Block '{key}' completed successfully.")
        return (key, result)
    except Exception as e:
        logger.error(f"  Block '{key}' failed: {e}", exc_info=True)
        return (key, {
            "response_type": "error",
            "summary": f"Error en bloque '{key}': {str(e)}",
            "content": [{"type": "text", "payload": f"[Error: {str(e)}]", "variant": "error"}]
        })


async def generate_executive_report(
    periodo_anomes: str,
    uo2_filter: Optional[str] = None,
    sections: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    **SOLO USAR CUANDO EL USUARIO EXPLÍCITAMENTE PIDA UN "REPORTE EJECUTIVO".**

    Genera un Reporte Ejecutivo holístico con múltiples secciones (KPIs, análisis por segmento, insights de IA).

    **Cuándo usar esta herramienta**:
    - Usuario dice: "Reporte ejecutivo de [periodo]"
    - Usuario dice: "Reporte de rotación de [periodo]"
    - Usuario dice: "Dashboard ejecutivo"

    **Cuándo NO usar esta herramienta** (usar execute_semantic_query en su lugar):
    - Usuario pide UNA métrica específica: "Tasa de rotación de 2025"
    - Usuario pide UN gráfico: "Evolución de ceses"
    - Usuario pide UNA tabla: "Listado de ceses"

    Args:
        periodo_anomes: Target period.
            - Use 'YYYY' (e.g., '2025') for FULL YEAR reports.
            - Use 'YYYYMM' (e.g., '202511') for MONTHLY reports.
            - Use 'YYYYQ#' (e.g., '2025Q1') for QUARTERLY reports.
        uo2_filter: Optional Division/Unit filter (e.g., 'DIVISION TALENTO'). Defaults to 'Global'.
        sections: Optional list of section keys to generate. Defaults to all sections.
            Valid keys: headline_current, headline_previous, annual_stats, segmentation, voluntary, talent, trend
    """
    try:
        parsed = parse_period(periodo_anomes)
        prev_p = get_previous_period(periodo_anomes)
        scope = uo2_filter or "Global"

        # Context label for report title
        granularity = parsed["granularity"]
        if granularity == "YEAR":
            label_period = f"AÑO {parsed['year']}"
        elif granularity == "QUARTER":
            label_period = parsed["display"]
        else:
            label_period = parsed["display"]
        ctx_label = f"{label_period} | {scope}"

        # Initialize snapshot
        snapshot_svc = ReportSnapshotService()
        report_id = snapshot_svc.create_snapshot(periodo_anomes, scope)
        logger.info(f"Started Report: {report_id} (Granularity: {granularity})")

        # 1. Build deterministic query specs (NO Gemini calls)
        all_blocks = _build_report_blocks(parsed, prev_p, uo2_filter)

        # 2. Filter by requested sections
        if sections:
            valid_sections = [s for s in sections if s in all_blocks]
            if not valid_sections:
                valid_sections = list(all_blocks.keys())
        else:
            valid_sections = list(all_blocks.keys())

        blocks_to_run = {k: all_blocks[k] for k in valid_sections}

        # 3. Execute ALL blocks in parallel via ThreadPoolExecutor
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(_executor, _execute_block, key, spec, ctx_label)
            for key, spec in blocks_to_run.items()
        ]

        logger.info(f"Dispatching {len(futures)} blocks in parallel...")
        completed = await asyncio.gather(*futures)

        # Collect results (includes both successes and graceful errors)
        results = dict(completed)

        # Count failures for logging
        failed = [k for k, v in results.items() if v.get("response_type") == "error"]
        if failed:
            logger.warning(f"Blocks with errors: {failed}")

        # 4. Store snapshot
        snapshot_svc.update_snapshot(report_id, results, status="DATA_GATHERED")

        # 5. Generate holistic narratives (only if we have meaningful data)
        successful_results = {k: v for k, v in results.items() if v.get("response_type") != "error"}
        ai_narratives = {}
        if successful_results:
            logger.info(f"Generating narratives for {report_id}...")
            ai_gen = ReportInsightGenerator()
            ai_narratives = await loop.run_in_executor(
                _executor, ai_gen.generate_report_narratives, successful_results, ctx_label
            )
            snapshot_svc.save_narratives(report_id, ai_narratives)

        # 6. Assemble Visual Package
        content_blocks = [
            {"type": "text", "payload": f"Reporte Ejecutivo: {ctx_label}", "variant": "h2"},
            {"type": "text", "payload": ai_narratives.get("critical_insight", "Generando resumen..."), "variant": "insight"}
        ]

        # Headline KPIs
        if "headline_current" in results:
            content_blocks.extend(results["headline_current"].get("content", []))

        # Segmentation
        if "segmentation" in results:
            content_blocks.append({"type": "text", "payload": "Análisis por Segmento", "variant": "h3"})
            content_blocks.extend(results["segmentation"].get("content", []))
            content_blocks.append({"type": "text", "payload": ai_narratives.get("segmentation", ""), "variant": "standard"})

        # Voluntary
        if "voluntary" in results:
            content_blocks.append({"type": "text", "payload": "Distribución de Rotación Voluntaria", "variant": "h3"})
            content_blocks.extend(results["voluntary"].get("content", []))
            content_blocks.append({"type": "text", "payload": ai_narratives.get("voluntary_trend", ""), "variant": "standard"})

        # Talent
        if "talent" in results and results["talent"].get("content"):
            content_blocks.append({"type": "text", "payload": "Fuga de Talento Crítico", "variant": "h3"})
            content_blocks.extend(results["talent"].get("content", []))
            content_blocks.append({"type": "text", "payload": ai_narratives.get("talent_leakage", ""), "variant": "insight"})

        # Trend
        if "trend" in results:
            content_blocks.append({"type": "text", "payload": "Evolución de Rotación", "variant": "h3"})
            content_blocks.extend(results["trend"].get("content", []))

        # Strategic Conclusion
        content_blocks.append({"type": "text", "payload": "Conclusión Estratégica", "variant": "h3"})
        content_blocks.append({"type": "text", "payload": ai_narratives.get("strategic_conclusion", ""), "variant": "standard"})

        # Recommendations
        recs = ai_narratives.get("recommendations")
        if recs:
            if isinstance(recs, list):
                recs_text = "\n".join([f"• {r}" for r in recs])
            else:
                recs_text = str(recs)
            content_blocks.append({"type": "text", "payload": "Recomendaciones Tácticas (AI Expert)", "variant": "h3"})
            content_blocks.append({"type": "text", "payload": recs_text, "variant": "insight"})

        return _sanitize_output({
            "response_type": "visual_package",
            "summary": f"Reporte Ejecutivo de Rotación - ID: {report_id}",
            "content": content_blocks,
            "metadata": {"report_id": report_id, "failed_blocks": failed}
        })

    except Exception as e:
        logger.error(f"Error in Executive Report Orchestrator: {e}", exc_info=True)
        return {"response_type": "error", "summary": f"Error: {str(e)}", "content": []}


def _sanitize_output(payload: Dict) -> Dict:
    """Recursively clean payload for JSON safety (NaN, Inf → None)."""
    def clean(obj):
        if isinstance(obj, list): return [clean(x) for x in obj]
        if isinstance(obj, dict): return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)): return None
        return obj
    return clean(payload)
