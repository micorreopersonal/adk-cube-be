from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import asyncio
import re
from dateutil.relativedelta import relativedelta

# Semantic Engine Integration
from app.ai.tools.universal_analyst import execute_semantic_query
from app.schemas.payloads import (
    VisualDataPackage, VisualBlock, TextBlock, KPIBlock, KPIItem, 
    ChartBlock, ChartPayload, ChartMetadata, TableBlock, TablePayload,
    Dataset, MetricFormat
)
from app.core.analytics.registry import DEFAULT_LISTING_COLUMNS
from google.genai import types, Client
import os

logger = logging.getLogger(__name__)

# ============================================================================
# PERIOD UTILITIES
# ============================================================================

def parse_period(periodo: str) -> Dict:
    """
    Parse period string in YYYY, YYYYQN, or YYYYMM format.
    
    Returns:
        Dict with keys: granularity, year, quarter, month, original, display
    """
    periodo = periodo.strip()
    
    # Year format: YYYY
    if re.match(r'^\d{4}$', periodo):
        year = int(periodo)
        return {
            "granularity": "YEAR",
            "year": year,
            "quarter": None,
            "month": None,
            "original": periodo,
            "display": f"Año {year}"
        }
    
    # Quarter format: YYYYQN
    quarter_match = re.match(r'^(\d{4})Q([1-4])$', periodo, re.IGNORECASE)
    if quarter_match:
        year = int(quarter_match.group(1))
        quarter = int(quarter_match.group(2))
        return {
            "granularity": "QUARTER",
            "year": year,
            "quarter": quarter,
            "month": None,
            "original": periodo,
            "display": f"Q{quarter} {year}"
        }
    
    # Month format: YYYYMM
    if re.match(r'^\d{6}$', periodo):
        year = int(periodo[:4])
        month = int(periodo[4:6])
        if 1 <= month <= 12:
            month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                          "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            return {
                "granularity": "MONTH",
                "year": year,
                "quarter": None,
                "month": month,
                "original": periodo,
                "display": f"{month_names[month-1]} {year}"
            }
    
    raise ValueError(f"Invalid period format '{periodo}'. Use YYYY, YYYYQN, or YYYYMM.")


def get_previous_period(periodo: str) -> str:
    """Calculate the previous period based on granularity."""
    parsed = parse_period(periodo)
    
    if parsed["granularity"] == "YEAR":
        return str(parsed["year"] - 1)
    elif parsed["granularity"] == "QUARTER":
        if parsed["quarter"] == 1:
            return f"{parsed['year'] - 1}Q4"
        else:
            return f"{parsed['year']}Q{parsed['quarter'] - 1}"
    elif parsed["granularity"] == "MONTH":
        current_date = datetime(parsed["year"], parsed["month"], 1)
        prev_date = current_date - relativedelta(months=1)
        return prev_date.strftime("%Y%m")
    
    raise ValueError(f"Unknown granularity: {parsed['granularity']}")


def get_ytd_range(periodo: str) -> Tuple[str, str]:
    """Calculate Year-to-Date range based on granularity."""
    parsed = parse_period(periodo)
    
    if parsed["granularity"] == "YEAR":
        prev_year = str(parsed["year"] - 1)
        return (prev_year, prev_year)
    elif parsed["granularity"] == "QUARTER":
        start_q = f"{parsed['year']}Q1"
        end_q = parsed["original"]
        return (start_q, end_q)
    elif parsed["granularity"] == "MONTH":
        start_month = f"{parsed['year']}01"
        end_month = parsed["original"]
        return (start_month, end_month)
    
    raise ValueError(f"Unknown granularity: {parsed['granularity']}")


# ============================================================================
# LLM NARRATIVE GENERATION
# ============================================================================

def generate_critical_insight(
    periodo_display: str,
    headline_data: Dict[str, float],
    prev_data: Dict[str, float],
    annual_stats: Dict[str, float],
    granularity: str
) -> str:
    """
    Generate AI-powered narrative analysis for the Critical Insight section.
    
    Args:
        periodo_display: Human-readable period (e.g., "Diciembre 2025")
        headline_data: Current period KPIs
        prev_data: Previous period KPIs for comparison
        annual_stats: Annual average stats for context
        granularity: YEAR | QUARTER | MONTH
    
    Returns:
        Markdown-formatted narrative text
    """
    try:
        # Initialize Vertex AI Client
        client = Client(
            vertexai=True,
            project=os.getenv("PROJECT_ID"),
            location=os.getenv("REGION", "us-central1")
        )
        
        # Prepare context data
        tasa_actual = headline_data.get("Tasa de Rotación Global (%)", 0)
        ceses_actual = headline_data.get("Total Ceses", 0)
        hc_actual = headline_data.get("Headcount Promedio", 0)
        
        tasa_prev = prev_data.get("Tasa de Rotación Global (%)", 0)
        ceses_prev = prev_data.get("Total Ceses", 0)
        hc_prev = prev_data.get("Headcount Promedio", 0)
        
        tasa_anual_avg = annual_stats.get("tasa_rotacion_avg", 0)
        
        delta_tasa = tasa_actual - tasa_prev
        delta_ceses = ceses_actual - ceses_prev
        delta_hc = hc_actual - hc_prev
        
        delta_anual_pct = 0
        if tasa_anual_avg > 0:
            delta_anual_pct = ((tasa_actual - tasa_anual_avg) / tasa_anual_avg) * 100
        
        # Determine period context
        period_context = {
            "YEAR": "anual",
            "QUARTER": "trimestral",
            "MONTH": "mensual"
        }.get(granularity, "mensual")
        
        # Build prompt
        prompt = f"""Eres un analista senior de RRHH especializado en rotación de personal. 
        
Analiza los siguientes datos de rotación del período {periodo_display} y genera un insight crítico ejecutivo.

**Datos Actuales ({periodo_display}):**
- Tasa de Rotación: {tasa_actual:.2f}%
- Total Ceses: {int(ceses_actual)}

**Comparativa Mensual (vs Mes Anterior):**
- Variación Tasa: {delta_tasa:+.2f} pts
- Variación Ceses: {delta_ceses:+.0f}

**Contexto Anual (Promedio Año):**
- Promedio Tasa Anual: {tasa_anual_avg:.2f}%
- Variación vs Promedio: {delta_anual_pct:+.1f}%

**Instrucciones:**
1. Escribe un párrafo de "Insight Crítico" similiar a este estilo:
   "La tasa de rotación mensual cerró en X%, marcando el punto más alto del año. Este resultado representa un incremento de Y pts respecto al mes anterior y se sitúa un Z% por encima del promedio anual."
2. Menciona si la tendencia es Alza Crítica, Estable o Mejora.
3. Identifica riesgos potenciales si la variación vs promedio es alta (>15%).
4. Usa tono ejecutivo, directo y basado en datos. Máximo 80 palabras.

**Formato de salida:** Texto plano en español, sin markdown headers.
"""
        
        # Generate narrative
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,  # Low temperature for factual analysis
                max_output_tokens=300
            )
        )
        
        narrative = response.text.strip()
        logger.info(f"✅ Generated critical insight narrative ({len(narrative)} chars)")
        return narrative
        
    except Exception as e:
        logger.error(f"❌ Failed to generate narrative: {e}")
        # Fallback to placeholder
        return "[Análisis narrativo no disponible.]"


# ============================================================================
# QUERY SEQUENCE BUILDER
# ============================================================================

def build_query_sequence(periodo: str, uo2_filter: Optional[str] = None) -> List[Dict]:
    """
    Build the sequence of semantic queries for the executive report.
    
    Args:
        periodo: Period in YYYY, YYYYQN, or YYYYMM format
        uo2_filter: Optional division filter
    
    Returns:
        List of query configurations, one per report section
    """
    parsed = parse_period(periodo)
    prev_period = get_previous_period(periodo)
    
    # Generate correct filters based on granularity
    base_filters = []
    
    if parsed["granularity"] == "YEAR":
        # For Annual, filter by "anio" dimension
        base_filters.append({"dimension": "anio", "value": parsed["year"]})
    elif parsed["granularity"] == "QUARTER":
        # For Quarterly, filter by "anio" and "trimestre"
        base_filters.append({"dimension": "anio", "value": parsed["year"]})
        base_filters.append({"dimension": "trimestre", "value": parsed["quarter"]})
    elif parsed["granularity"] == "MONTH":
        # For Monthly, filter by "periodo" (YYYYMM)
        base_filters.append({"dimension": "periodo", "value": parsed["original"]})
    
    # Add Division Filter if present
    if uo2_filter:
        base_filters.append({"dimension": "uo2", "value": uo2_filter})
    
    queries = [
        # 1. Headline KPIs (Current Period)
        {
            "section": "headline_current",
            "intent": "SNAPSHOT",
            "cube_query": {
                "metrics": ["tasa_rotacion", "ceses_totales", "headcount_promedio"],
                "dimensions": [],
                "filters": base_filters
            },
            "metadata": {"requested_viz": "KPI_ROW"}
        },
        
        # 2. Headline KPIs (Previous Period)
        {
            "section": "headline_previous",
            "intent": "SNAPSHOT",
            "cube_query": {
                "metrics": ["tasa_rotacion", "ceses_totales", "headcount_promedio"],
                "dimensions": [],
                "filters": [{"dimension": "periodo", "value": prev_period}] + ([{"dimension": "uo2", "value": uo2_filter}] if uo2_filter else [])
            },
            "metadata": {"requested_viz": "KPI_ROW"}
        },
        
        # 3. YTD Trend (For Annual Averages calculation)
        {
            "section": "ytd_trend",
            "intent": "TREND",
            "cube_query": {
                "metrics": ["tasa_rotacion", "ceses_totales", "headcount_promedio"],
                "dimensions": ["mes"],
                "filters": [{"dimension": "anio", "value": parsed["year"]}] + ([{"dimension": "uo2", "value": uo2_filter}] if uo2_filter else [])
            },
            "metadata": {"requested_viz": "LINE_CHART"} # Hidden viz, used for stats
        },
        
        # 4. Segmentation Snapshot (FFVV vs ADMIN - Current Period)
        {
            "section": "segmentation_snapshot",
            "intent": "COMPARISON",
            "cube_query": {
                "metrics": ["tasa_rotacion", "ceses_totales"],
                "dimensions": ["grupo_segmento"],
                "filters": base_filters
            },
            "metadata": {
                "requested_viz": "BAR_CHART", 
                "title_suggestion": "Rotación por Segmento (Actual)"
            }
        },
        
        # 5. Global Comparative Snapshot (Voluntary vs Involuntary)
        {
            "section": "global_breakdown",
            "intent": "SNAPSHOT",
            "cube_query": {
                "metrics": ["tasa_rotacion_voluntaria", "tasa_rotacion_involuntaria"],
                "dimensions": [],
                "filters": base_filters
            },
            "metadata": {
                "requested_viz": "PIE_CHART",
                "title_suggestion": "Distribución Voluntaria vs Involuntaria"
            }
        },
        
        # 6. Voluntary Focus (Top Divisions)
        {
            "section": "voluntary_focus",
            "intent": "COMPARISON",
            "cube_query": {
                "metrics": ["tasa_rotacion_voluntaria", "ceses_voluntarios"],
                "dimensions": ["uo2"],
                "filters": base_filters,
                "limit": 5
            },
            "metadata": {
                "requested_viz": "TABLE",
                "title_suggestion": "Focos de Rotación Voluntaria (Top 5)"
            }
        },
        
        # 7. Talent Leakage (Detailed List)
        {
            "section": "talent_leakage",
            "intent": "LISTING",
            "cube_query": {
                "metrics": [],
                "dimensions": DEFAULT_LISTING_COLUMNS,
                "filters": base_filters + [
                    {"dimension": "talento", "value": ["HiPo", "HiPer"]},
                    {"dimension": "estado", "value": "Cesado"}
                ]
            },
            "metadata": {
                "requested_viz": "TABLE",
                "title_suggestion": "Fuga de Talento Crítico (Detalle)"
            }
        },
        
        # 8. Monthly Trend (Visual Context)
        {
            "section": "monthly_trend",
            "intent": "TREND",
            "cube_query": {
                "metrics": ["tasa_rotacion", "tasa_rotacion_voluntaria"],
                "dimensions": ["mes"],
                "filters": [{"dimension": "anio", "value": parsed["year"]}] + ([{"dimension": "uo2", "value": uo2_filter}] if uo2_filter else [])
            },
            "metadata": {
                "requested_viz": "LINE_CHART",
                "title_suggestion": f"Evolución Mensual - {parsed['year']}"
            }
        }
    ]
    
    return queries


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def generate_executive_report(periodo_anomes: str, uo2_filter: Optional[str] = None) -> dict:
    """
    Generate Executive Turnover Report by orchestrating sequential calls to universal_analyst.
    
    Args:
        periodo_anomes: Period in YYYY, YYYYQN, or YYYYMM format
        uo2_filter: Optional division filter
    
    Returns:
        VisualDataPackage with 7-section executive report
    """
    logger.info(f"🎯 [ORCHESTRATOR] Generating Executive Report for {periodo_anomes}")
    
    # Parse period
    try:
        parsed_period = parse_period(periodo_anomes)
        prev_period = get_previous_period(periodo_anomes)
        logger.info(f"   📅 Period: {parsed_period['display']} | Previous: {prev_period}")
    except ValueError as e:
        return {"error": str(e)}
    
    # Build query sequence
    queries = build_query_sequence(periodo_anomes, uo2_filter)
    logger.info(f"   📋 Query sequence: {len(queries)} sections")
    
    # Execute queries sequentially
    results = {}
    for query_config in queries:
        section = query_config["section"]
        logger.info(f"   ⏳ Executing: {section}")
        
        # Extract limit if present in cube_query to pass as explicit argument
        limit = None
        if "limit" in query_config["cube_query"]:
            limit = query_config["cube_query"].pop("limit")
        
        try:
            result = execute_semantic_query(
                intent=query_config["intent"],
                cube_query=query_config["cube_query"],
                metadata=query_config.get("metadata", {}),
                limit=limit
            )
            results[section] = result
            logger.info(f"   ✅ {section} completed")
        except Exception as e:
            logger.error(f"   ❌ {section} failed: {e}")
            results[section] = {"content": [], "error": str(e)}
    
    # Extract KPI data for narrative and comparison
    headline_data = {}
    prev_data = {}
    annual_stats = {"tasa_rotacion_avg": 0, "ceses_avg": 0, "hc_avg": 0}
    
    # Extract from headline_current
    if "headline_current" in results and "content" in results["headline_current"]:
        content = results["headline_current"]["content"]
        if content and len(content) > 0:
            first_block = content[0]
            if hasattr(first_block, 'payload') and hasattr(first_block.payload, 'items'):
                for item in first_block.payload.items:
                    headline_data[item.label] = item.value
    
    # Extract from headline_previous
    if "headline_previous" in results and "content" in results["headline_previous"]:
        content = results["headline_previous"]["content"]
        if content and len(content) > 0:
            first_block = content[0]
            if hasattr(first_block, 'payload') and hasattr(first_block.payload, 'items'):
                for item in first_block.payload.items:
                    prev_data[item.label] = item.value
    
    # Calculate Annual Averages from YTD Trend
    if "ytd_trend" in results and "content" in results["ytd_trend"]:
        content = results["ytd_trend"]["content"]
        if content and len(content) > 0:
            # Assuming Single Dataset for each metric in Trend Line or similar structure
            # But execute_semantic_query returns ChartPayload for TREND intent
            chart_block = content[0]
            if hasattr(chart_block, 'payload') and hasattr(chart_block.payload, 'datasets'):
                datasets = chart_block.payload.datasets
                
                # Helper to get average from a dataset label
                def get_avg_from_dataset(label_key):
                    for ds in datasets:
                        if label_key in ds.label.lower():
                            values = [v for v in ds.data if v is not None]
                            return sum(values) / len(values) if values else 0
                    return 0
                
                annual_stats["tasa_rotacion_avg"] = get_avg_from_dataset("tasa")
                annual_stats["ceses_avg"] = get_avg_from_dataset("ceses")
                annual_stats["hc_avg"] = get_avg_from_dataset("headcount")

    # Generate LLM narrative for Insight Crítico
    narrative = generate_critical_insight(
        periodo_display=parsed_period['display'],
        headline_data=headline_data,
        prev_data=prev_data,
        annual_stats=annual_stats, # Pass annual context
        granularity=parsed_period['granularity']
    )
    
    # Assemble VisualDataPackage
    blocks = []
    
    # Title
    blocks.append(TextBlock(payload=f"Reporte Ejecutivo de Rotación - {parsed_period['display']}", variant="h2"))
    
    # Section 1: Insight Crítico
    blocks.append(TextBlock(payload="1. Insight Crítico", variant="h3"))
    blocks.append(TextBlock(payload=narrative, variant="standard"))
    if "headline_current" in results:
        blocks.extend(results["headline_current"].get("content", []))
    
    # Section 2: Segmentación
    blocks.append(TextBlock(payload="2. Segmentación (ADMIN vs FFVV)", variant="h3"))
    if "segmentation_snapshot" in results:
        blocks.extend(results["segmentation_snapshot"].get("content", []))
    
    # Section 3: Rotación Voluntaria
    blocks.append(TextBlock(payload="3. Resumen de Rotación Voluntaria", variant="h3"))
    if "global_breakdown" in results:
        blocks.extend(results["global_breakdown"].get("content", []))
    
    # Section 3.1: Focos
    blocks.append(TextBlock(payload="3.1 Focos de Concentración (Top Divisiones)", variant="h3"))
    if "voluntary_focus" in results:
        blocks.extend(results["voluntary_focus"].get("content", []))
    
    # Section 4: Fuga de Talento
    blocks.append(TextBlock(payload="4. Alerta de Talento Clave", variant="h3"))
    blocks.append(TextBlock(payload="Colaboradores clave (HiPo/HiPer) salientes en el periodo:", variant="standard"))
    if "talent_leakage" in results:
        blocks.extend(results["talent_leakage"].get("content", []))
    
    # Section 5: Tabla Comparativa vs Promedio Anual
    blocks.append(TextBlock(payload="5. Tabla Comparativa (vs. Promedio Anual)", variant="h3"))
    
    # Construct Manual Table for Section 5
    try:
        current_hc = headline_data.get("Headcount Promedio", 0)
        current_ceses = headline_data.get("Total Ceses", 0)
        current_rate = headline_data.get("Tasa de Rotación Global (%)", 0)
        
        avg_hc = annual_stats["hc_avg"]
        avg_ceses = annual_stats["ceses_avg"]
        avg_rate = annual_stats["tasa_rotacion_avg"]
        
        def safe_delta_pct(curr, base):
            if base == 0: return "N/A"
            delta = ((curr - base) / base) * 100
            return f"{delta:+.1f}%"

        comp_table_rows = [
            {"Indicador": "HC Activo Promedio", "Mes Actual": f"{int(current_hc)}", "Promedio Anual": f"{int(avg_hc)}", "Variación": safe_delta_pct(current_hc, avg_hc)},
            {"Indicador": "Ceses Totales", "Mes Actual": f"{int(current_ceses)}", "Promedio Anual": f"{int(avg_ceses)}", "Variación": safe_delta_pct(current_ceses, avg_ceses)},
            {"Indicador": "Tasa Rotación (%)", "Mes Actual": f"{current_rate:.2f}%", "Promedio Anual": f"{avg_rate:.2f}%", "Variación": f"{current_rate - avg_rate:+.2f} pts"}
        ]
        
        blocks.append(TableBlock(payload=TablePayload(rows=comp_table_rows)))
        
    except Exception as e:
        logger.error(f"Error constructing comparative table: {e}")
    
    # Section 6: Monthly Trend
    blocks.append(TextBlock(payload="6. Tendencia Anual", variant="h3"))
    if "monthly_trend" in results:
        blocks.extend(results["monthly_trend"].get("content", []))

    # Section 7: Strategic Conclusion (Placeholder for full LLM implementation)
    # Ideally, this would be another LLM call with all previous context
    
    logger.info(f"✅ [ORCHESTRATOR] Report generated with {len(blocks)} blocks")
    
    return VisualDataPackage(
        response_type="visual_package",
        summary=f"Reporte Ejecutivo de Rotación - {parsed_period['display']}",
        content=blocks
    ).model_dump()
