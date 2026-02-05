from typing import Dict, Any, List, Optional
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import asyncio
import re
from dateutil.relativedelta import relativedelta

# Semantic Engine Integation
from app.ai.tools.universal_analyst import execute_semantic_query
from app.core.analytics.registry import DIMENSIONS_REGISTRY
from app.schemas.payloads import (
    VisualDataPackage, VisualBlock, TextBlock, KPIBlock, KPIItem, 
    ChartBlock, ChartPayload, ChartMetadata, TableBlock, TablePayload,
    Dataset, MetricFormat
)
from google.genai import types, Client
import os

logger = logging.getLogger(__name__)

# ============================================================================
# PERIOD UTILITIES (Year/Quarter/Month Agnostic)
# ============================================================================

def parse_period(periodo: str) -> Dict:
    """
    Detect period granularity and extract components.
    
    Supported formats:
    - Year: "2025" (YYYY)
    - Quarter: "2025Q1" (YYYYQN)
    - Month: "202512" (YYYYMM)
    
    Returns:
        {
            "granularity": "YEAR" | "QUARTER" | "MONTH",
            "year": int,
            "quarter": int | None,
            "month": int | None,
            "original": str,
            "display": str  # Human-readable format
        }
    """
    periodo = str(periodo).strip()
    
    # Year: YYYY (4 digits)
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
    
    # Quarter: YYYYQN (e.g., 2025Q1)
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
    
    # Month: YYYYMM (6 digits)
    if re.match(r'^\d{6}$', periodo):
        year = int(periodo[:4])
        month = int(periodo[4:6])
        if month < 1 or month > 12:
            raise ValueError(f"Invalid month in period '{periodo}'. Month must be 01-12.")
        
        # Spanish month names
        month_names = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        
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
    """
    Calculate the previous period based on granularity.
    
    Examples:
    - "2025" → "2024"
    - "2025Q1" → "2024Q4"
    - "202501" → "202412"
    """
    parsed = parse_period(periodo)
    
    if parsed["granularity"] == "YEAR":
        return str(parsed["year"] - 1)
    
    elif parsed["granularity"] == "QUARTER":
        if parsed["quarter"] == 1:
            # Q1 → Previous Year Q4
            return f"{parsed['year'] - 1}Q4"
        else:
            # Q2/Q3/Q4 → Same Year Previous Quarter
            return f"{parsed['year']}Q{parsed['quarter'] - 1}"
    
    elif parsed["granularity"] == "MONTH":
        current_date = datetime(parsed["year"], parsed["month"], 1)
        prev_date = current_date - relativedelta(months=1)
        return prev_date.strftime("%Y%m")
    
    raise ValueError(f"Unknown granularity: {parsed['granularity']}")


def get_ytd_range(periodo: str) -> Tuple[str, str]:
    """
    Calculate the YTD (Year-To-Date) range based on granularity.
    
    Returns:
        (start_period, end_period)
    
    Examples:
    - "2025" → ("2024", "2024") # Compare against previous year
    - "2025Q3" → ("2025Q1", "2025Q3") # Q1 to Q3
    - "202509" → ("202501", "202509") # Jan to Sep
    """
    parsed = parse_period(periodo)
    
    if parsed["granularity"] == "YEAR":
        # For annual reports, compare against previous year
        prev_year = str(parsed["year"] - 1)
        return (prev_year, prev_year)
    
    elif parsed["granularity"] == "QUARTER":
        # YTD = Q1 to current quarter
        start_q = f"{parsed['year']}Q1"
        end_q = parsed["original"]
        return (start_q, end_q)
    
    elif parsed["granularity"] == "MONTH":
        # YTD = January to current month
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
    granularity: str
) -> str:
    """
    Generate AI-powered narrative analysis for the Critical Insight section.
    
    Args:
        periodo_display: Human-readable period (e.g., "Diciembre 2025")
        headline_data: Current period KPIs
        prev_data: Previous period KPIs for comparison
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
        
        delta_tasa = tasa_actual - tasa_prev
        delta_ceses = ceses_actual - ceses_prev
        delta_hc = hc_actual - hc_prev
        
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
- Headcount Promedio: {int(hc_actual)}

**Datos Período Anterior:**
- Tasa de Rotación: {tasa_prev:.2f}%
- Total Ceses: {int(ceses_prev)}
- Headcount Promedio: {int(hc_prev)}

**Variaciones:**
- Δ Tasa: {delta_tasa:+.2f} puntos porcentuales
- Δ Ceses: {delta_ceses:+.0f}
- Δ Headcount: {delta_hc:+.0f}

**Instrucciones:**
1. Genera un análisis {period_context} conciso (máximo 3 párrafos)
2. Identifica el hallazgo más crítico (tendencia, riesgo, o logro)
3. Contextualiza las variaciones (¿son significativas? ¿preocupantes?)
4. Usa un tono profesional pero directo
5. NO uses bullet points, escribe en párrafos narrativos
6. NO repitas los números exactos (ya están en los KPIs)
7. Enfócate en el "¿qué significa esto?" y "¿por qué importa?"

**Formato de salida:** Texto plano en español, sin markdown headers.
"""
        
        # Generate narrative
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,  # Low temperature for factual analysis
                max_output_tokens=500
            )
        )
        
        narrative = response.text.strip()
        logger.info(f"✅ Generated critical insight narrative ({len(narrative)} chars)")
        return narrative
        
    except Exception as e:
        logger.error(f"❌ Failed to generate narrative: {e}")
        # Fallback to placeholder
        return "[Análisis narrativo no disponible. Revise los KPIs a continuación para evaluar el estado de la rotación.]"


async def get_executive_turnover_report(periodo_anomes: str, uo2_filter: Optional[str] = None) -> dict:
    """
    Genera el Reporte Ejecutivo de Rotación en formato Visual Data Package.
    
    Soporta múltiples granularidades:
    - Anual: "2025" (YYYY)
    - Trimestral: "2025Q1" (YYYYQN)
    - Mensual: "202512" (YYYYMM)
    
    Args:
        periodo_anomes: Período en formato YYYY, YYYYQN, o YYYYMM
        uo2_filter: Filtro opcional de División (UO2)
    
    Returns:
        VisualDataPackage con bloques estructurados (KPI, Charts, Tables, Text)
    """
    logger.info(f"📊 Generating Executive Turnover Report for {periodo_anomes}...")
    
    # Parse Period and Calculate Derived Periods
    try:
        parsed_period = parse_period(periodo_anomes)
        prev_period = get_previous_period(periodo_anomes)
        ytd_start, ytd_end = get_ytd_range(periodo_anomes)
        
        logger.info(f"   ⏱️ Granularity: {parsed_period['granularity']}")
        logger.info(f"   📅 Current: {parsed_period['display']}")
        logger.info(f"   ⬅️ Previous: {prev_period}")
        logger.info(f"   📊 YTD Range: {ytd_start} to {ytd_end}")
        
    except ValueError as e:
        return {"error": str(e)}

    # Base Filters
    base_filters = [{"dimension": "periodo", "value": periodo_anomes}]
    if uo2_filter:
        base_filters.append({"dimension": "uo2", "value": uo2_filter})

    # --- SECTION A: HEADLINE METRICS (Summary) ---
    logger.info("   👉 Fetching Headline Metrics...")
    # metrics: Tasa, Ceses, HC
    headline_req = {
        "intent": "SNAPSHOT",
        "cube_query": {
            "metrics": ["tasa_rotacion", "ceses_totales", "headcount_promedio"],
            "dimensions": [], # Global aggregated
            "filters": base_filters
        },
        "metadata": {"requested_viz": "KPI_ROW"}
    }
    headline_resp = execute_semantic_query(**headline_req)
    
    # Extraer valores numéricos seguros
    headline_data = {}
    if headline_resp.get("content"):
        # Safe Payload Extraction (Handle List vs Dict structure)
        first_block = headline_resp["content"][0]
        # Some serializers might flatten payload if it's just items
        payload = first_block.get("payload", {})
        
        items = []
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("items", [])
            
        for item in items:
            # Handle both Obj (Pydantic) and Dict
            label = item.get("label") if isinstance(item, dict) else getattr(item, "label", "Unknown")
            value = item.get("value") if isinstance(item, dict) else getattr(item, "value", 0)
            headline_data[label] = value
    
    # --- SECTION B: SEGMENTATION (ADMIN vs FFVV) ---
    logger.info("   👉 Fetching Segmentation (ADMIN/FFVV)...")
    # Use calculated "grupo_segmento" dimension for automatic FFVV/ADMIN grouping
    seg_req = {
        "intent": "COMPARISON",
        "cube_query": {
            "metrics": ["tasa_rotacion", "ceses_totales"],
            "dimensions": ["grupo_segmento"],  # Calculated dimension that groups segmento values
            "filters": base_filters
        },
        "metadata": {"requested_viz": "TABLE"} 
    }
    seg_resp = execute_semantic_query(**seg_req)
    
    # Safe Payload Extraction for Segmentation
    rows = []
    if seg_resp.get("content") if isinstance(seg_resp, dict) else getattr(seg_resp, "content", []):
        content = seg_resp.get("content", []) if isinstance(seg_resp, dict) else getattr(seg_resp, "content", [])
        if content:
             first = content[0]
             # Handle Pydantic Block object or Dict
             payload = first.get("payload", {}) if isinstance(first, dict) else getattr(first, "payload", {})
             # Handle Pydantic Payload object or Dict
             rows = payload.get("rows", []) if isinstance(payload, dict) else getattr(payload, "rows", [])

    seg_data = rows


    # --- SECTION C: VOLUNTARY FOCUS (Top 5 Divisions) ---
    logger.info("   👉 Fetching Voluntary Focus...")
    # Filtro adicional de 'renuncia' implícito en la métrica 'tasa_rotacion_voluntaria'
    vol_req = {
        "intent": "COMPARISON",
        "cube_query": {
            "metrics": ["tasa_rotacion_voluntaria", "ceses_voluntarios"],
            "dimensions": ["uo2"],
            "filters": base_filters
        },
        # TODO: Implementar Sorting desc en universal_analyst si no existe. 
        # Por ahora ordenamos en memoria aquí.
        "metadata": {"requested_viz": "TABLE"}
    }
    vol_resp = execute_semantic_query(**vol_req)
    
    # Safe Payload Extraction for Voluntary
    vol_rows = []
    if vol_resp.get("content") if isinstance(vol_resp, dict) else getattr(vol_resp, "content", []):
         content = vol_resp.get("content", []) if isinstance(vol_resp, dict) else getattr(vol_resp, "content", [])
         if content:
             first = content[0]
             payload = first.get("payload", {}) if isinstance(first, dict) else getattr(first, "payload", {})
             vol_rows = payload.get("rows", []) if isinstance(payload, dict) else getattr(payload, "rows", [])

    # Sort descending by tasa
    vol_rows.sort(key=lambda x: (x.get("tasa_rotacion_voluntaria", 0) if isinstance(x, dict) else getattr(x, "tasa_rotacion_voluntaria", 0)) or 0, reverse=True)
    top_5_voluntary = vol_rows[:5]

    # --- SECTION D: TALENT LEAKAGE (Hipers / Hipos) ---
    logger.info("   👉 Fetching Talent Leakage...")
    # Filtro: Talento IN [7, 8, 9] (Asumiendo estos valores o strings equivalentes en DB)
    # IMPORTANTE: Ajustar valores según los datos reales de 'mapeo_talento_ultimo_anio'
    talent_filters = base_filters.copy()
    talent_filters.append({"dimension": "estado", "value": "Cesado"})
    # Asumimos que el backend entiende una lista en value para IN
    talent_filters.append({"dimension": "talento", "value": ["7", "8", "9", "Top Performer", "High Potential"]}) 

    leak_req = {
        "intent": "LISTING",
        "cube_query": {
            "metrics": [], # Solo atributos
            "dimensions": ["nombre", "posicion", "uo2", "talento", "motivo"],
            "filters": talent_filters
        },
        "metadata": {"requested_viz": "TABLE"}
    }
    leak_resp = execute_semantic_query(**leak_req)
    # Safe Payload Extraction for Leakage
    leak_rows = []
    if leak_resp.get("content") if isinstance(leak_resp, dict) else getattr(leak_resp, "content", []):
         content = leak_resp.get("content", []) if isinstance(leak_resp, dict) else getattr(leak_resp, "content", [])
         if content:
             first = content[0]
             payload = first.get("payload", {}) if isinstance(first, dict) else getattr(first, "payload", {})
             leak_rows = payload.get("rows", []) if isinstance(payload, dict) else getattr(payload, "rows", [])

    # Clasificar Hipers vs Hipos
    hipers_list = []
    hipos_list = []
    for row in leak_rows:
        t_val = str(row.get("talento", "") if isinstance(row, dict) else getattr(row, "talento", "")).lower()
        if "7" in t_val or "top" in t_val:
            hipers_list.append(row)
        elif "8" in t_val or "9" in t_val or "potential" in t_val:
            hipos_list.append(row)

    # --- SECTION E: COMPARISON HISTORY (Section 5 & Insight Support) ---
    logger.info("   👉 Fetching Comparative Context (Prev Month & YTD)...")
    
    # 1. Previous Month Metrics (For MoM Variation)
    prev_req = {
        "intent": "SNAPSHOT",
        "cube_query": {
            "metrics": ["tasa_rotacion", "ceses_totales", "headcount_promedio"],
            "dimensions": [],
            "filters": [{"dimension": "periodo", "value": prev_period}] + ([{"dimension": "uo2", "value": uo2_filter}] if uo2_filter else [])
        },
        "metadata": {"requested_viz": "KPI_ROW"}
    }
    prev_resp = execute_semantic_query(**prev_req)
    prev_data = {}
    if prev_resp.get("content"):
         # Safe Extract
         first = prev_resp["content"][0]
         payload = first.get("payload", {}) if isinstance(first, dict) else getattr(first, "payload", {})
         p_items = payload.get("items", []) if isinstance(payload, dict) else getattr(payload, "items", [])
         for item in p_items:
             lbl = item.get("label") if isinstance(item, dict) else getattr(item, "label", "Unknown")
             val = item.get("value") if isinstance(item, dict) else getattr(item, "value", 0)
             prev_data[lbl] = val

    # 2. Annual Average (YTD) - Simplified as "Snapshot of YTD" or "Average of Monthly Rates"
    # Ideally should query months from start_date to current_date and Avg.
    # We will simulate by querying the 'periodo' IN [Jan..Current] and averaging manually or via SQL if supported.
    # For robust implementation without complex iteration, we use a single query with aggregation if possible, 
    # OR simpler: just query year-to-date scalar if metrics support it.
    # Let's try LISTING of monthly rates and avg in python to be safe.
    
    # 2. YTD/Comparative Range Query
    # Use ytd_start and ytd_end to construct the period range
    # For YEAR granularity, this will be a single year (previous year)
    # For QUARTER/MONTH, this will be a range
    
    # Build period list based on granularity
    if parsed_period["granularity"] == "YEAR":
        # Single year comparison
        ytd_periods = [ytd_start]  # Previous year
    elif parsed_period["granularity"] == "QUARTER":
        # Q1 to current quarter
        ytd_periods = []
        for q in range(1, parsed_period["quarter"] + 1):
            ytd_periods.append(f"{parsed_period['year']}Q{q}")
    else:  # MONTH
        # January to current month
        ytd_periods = []
        start_month = int(ytd_start[4:6])
        end_month = int(ytd_end[4:6])
        for m in range(start_month, end_month + 1):
            ytd_periods.append(f"{parsed_period['year']}{m:02d}")
            
    ytd_req = {
        "intent": "TREND", # Use Trend to get monthly data
        "cube_query": {
            "metrics": ["tasa_rotacion", "ceses_totales", "headcount_promedio"],
            "dimensions": ["periodo"],
            "filters": [{"dimension": "periodo", "value": ytd_periods}] + ([{"dimension": "uo2", "value": uo2_filter}] if uo2_filter else [])
        },
        "metadata": {"requested_viz": "LINE_CHART"}
    }
    ytd_resp = execute_semantic_query(**ytd_req)
    # Calculate Averages from Chart Payload
    avg_data = {"tasa_rotacion": 0, "ceses_totales": 0, "headcount_promedio": 0}
    
    if ytd_resp.get("content"):
        # Safe Extract Chart
        first = ytd_resp["content"][0]
        payload = first.get("payload", {}) if isinstance(first, dict) else getattr(first, "payload", {})
        datasets = payload.get("datasets", []) if isinstance(payload, dict) else getattr(payload, "datasets", [])
        trends_labels = payload.get("labels", []) if isinstance(payload, dict) else getattr(payload, "labels", [])
        tasa_trends_data = []

        for ds in datasets:
            lbl = ds.get("label") if isinstance(ds, dict) else getattr(ds, "label", "")
            data_points = ds.get("data", []) if isinstance(ds, dict) else getattr(ds, "data", [])
            clean_points = [x for x in data_points if x is not None]
            
            if clean_points:
                avg_val = sum(clean_points) / len(clean_points)
                # Map Chart Labels back to canonical metric names for comparison
                # This is tricky because Chart labels are "Tasa de Rotación Global (%)" not "tasa_rotacion"
                # We do fuzzy matching or check order. 
                # Order in request: [tasa, ceses, hc] -> Datasets should match order if UniversalAnalyst preserves it.
                # Simplification: Map by Label text.
                if "Rotación" in lbl: 
                     avg_data["tasa_rotacion"] = avg_val
                     tasa_trends_data = clean_points # Capture for Chart
                elif "Ceses" in lbl: avg_data["ceses_totales"] = avg_val
                elif "Headcount" in lbl: avg_data["headcount_promedio"] = avg_val

    # --- Build Section 5: Comparative Table Data ---
    comp_rows = []
    
    # 1. HC Activo
    curr_hc = headline_data.get("Headcount Promedio", 0)
    avg_hc = avg_data.get("headcount_promedio", 0)
    var_hc = ((curr_hc - avg_hc) / avg_hc * 100) if avg_hc else 0
    comp_rows.append({
        "Indicador": "HC Activo (Dotación)",
        "Mes Actual": f"{int(curr_hc)}",
        f"Promedio {parsed_period['display']}": f"{int(avg_hc)}",
        "Variación": f"{var_hc:+.1f}%"
    })
    
    # 2. Ceses Totales
    curr_ceses = headline_data.get("Total Ceses", 0)
    avg_ceses = avg_data.get("ceses_totales", 0)
    var_ceses = ((curr_ceses - avg_ceses) / avg_ceses * 100) if avg_ceses else 0
    comp_rows.append({
        "Indicador": "Ceses Totales",
        "Mes Actual": f"{int(curr_ceses)}",
        f"Promedio {parsed_period['display']}": f"{avg_ceses:.1f}",
        "Variación": f"{var_ceses:+.1f}%"
    })
    
    # 3. Tasa Rotación
    curr_rate = headline_data.get("Tasa de Rotación Global (%)", 0)
    avg_rate = avg_data.get("tasa_rotacion", 0)
    diff_bp = (curr_rate - avg_rate) * 100 # Basis points
    comp_rows.append({
        "Indicador": "Tasa de Rotación",
        "Mes Actual": f"{curr_rate:.2f}%",
        f"Promedio {parsed_period['display']}": f"{avg_rate:.2f}%",
        "Variación": f"{diff_bp:+.0f} bp"
    })

    # --- CONSTRUCT FINAL JSON ---
    # --- CONSTRUCT STANDARD VISUAL BLOCKS ---
    
    # --- CONSTRUCT STANDARD VISUAL BLOCKS (7-POINT STRUCTURE) ---
    
    blocks = []
    
    # [HEADER] Dynamic Title
    title_text = f"Reporte Ejecutivo de Rotación - {parsed_period['display']}"
    blocks.append(TextBlock(payload=title_text, variant="h2"))
    
    # [SECTION 1] Insight Crítico (Narrative - Supported by KPIs)
    blocks.append(TextBlock(payload="1. Insight Crítico", variant="h3"))
    
    # Generate AI-powered narrative
    logger.info("   🤖 Generating Critical Insight narrative with LLM...")
    critical_insight_text = generate_critical_insight(
        periodo_display=parsed_period['display'],
        headline_data=headline_data,
        prev_data=prev_data,
        granularity=parsed_period['granularity']
    )
    blocks.append(TextBlock(payload=critical_insight_text, variant="standard"))
    
    kpi_items = []
    for label, value in headline_data.items():
        # KPI Formatting (User Req: 2 decimals, type ratio, symbol %)
        formatted_value = f"{float(value):.2f}"
        
        # Trend Context (User Req: 'vs que?')
        ctx_tooltip = None
        delta_str = None
        diff = 0  # Default
        
        if prev_data and label in prev_data:
            prev_val = float(prev_data[label])
            curr_val = float(value)
            diff = curr_val - prev_val
            
            # Contextual Delta
            delta_str = f"{diff:+.2f} pp vs Mes Ant." # pp = puntos porcentuales for rates
            if "tasa" not in label.lower():
                 delta_str = f"{diff:+.0f} vs Mes Ant."
            
            ctx_tooltip = f"Mes Actual: {curr_val:.2f} | Mes Anterior: {prev_val:.2f} | Var: {diff:+.2f}"

        # STATUS: Default to NEUTRAL (No automatic risk assessment)
        status = "NEUTRAL"

        kpi_items.append(KPIItem(
            label=label, 
            value=formatted_value, 
            delta=delta_str,
            status=status,
            tooltip=ctx_tooltip
        ))
    if kpi_items:
        blocks.append(KPIBlock(type="KPI_ROW", payload=kpi_items))

    # [SECTION 2] Segmentación (ADMI vs FFVV)
    blocks.append(TextBlock(payload="2. Segmentación (ADMI vs. FFVV)", variant="h3"))
    if seg_data:
        # PIVOT DATA FOR LINE CHART (ADMI vs FFVV)
        # Assuming seg_data comes from a SNAPSHOT query (one month). 
        # User wants a TREND LINE (Line Chart with 2 lines).
        # We need to fetch TREND data for these segments.
        # This requires a NEW query for Section 2 specifically.
        
        # New Query for Section 2: Trend Split by Segment
        seg_trend_req = {
            "intent": "TREND",
            "cube_query": {
                "metrics": ["tasa_rotacion"],
                "dimensions": ["periodo", "segmento"], 
                "filters": base_filters + [{"dimension": "segmento", "value": ["Administrativo", "Fuerza de Ventas"]}],
                "limit": 1000
            },
            "metadata": {"requested_viz": "LINE_CHART"}
        }
        seg_trend_resp = execute_semantic_query(**seg_trend_req)
        
        # Extract and Structure for ChartBlock
        seg_datasets = []
        seg_labels = []
        if seg_trend_resp.get("content"):
            first = seg_trend_resp["content"][0]
            payload = first.get("payload", {})
            # payload might be `datasets` if `universal_analyst` returns a chart payload directly?
            # Or rows if it returns raw data. 
            # `universal_analyst` returns a visual package or raw data.
            # Assuming it returns raw rows for LISTING/TREND unless manipulated.
            # Actually, `universal_analyst` for LINE_CHART returns `labels` and `datasets`.
            # If so, we can use it directly IF keys match.
            # If `universal_analyst` returns grouped data (Dataset per segment), we use it.
            
            # Defensive: Check if payload has datasets
            if "datasets" in payload and "labels" in payload:
                seg_labels = payload["labels"]
                seg_datasets = payload["datasets"]
            else:
                # Fallback: Pivot raw rows manually?
                # Ideally `universal_analyst` handles pivoting if dimensions are provided.
                pass

        blocks.append(ChartBlock(
            subtype="LINE", # USER REQUEST: Line Chart
            payload=ChartPayload(labels=seg_labels, datasets=seg_datasets),
            metadata=ChartMetadata(title="Evolución Comparativa: ADMI vs FFVV", y_axis_label="Tasa (%)")
        ))

    # [SECTION 3] Comparativa de Rotación (Total vs Voluntaria vs Involuntaria)
    # GLOBAL LEVEL - Not by division
    blocks.append(TextBlock(payload="3. Comparativa de Rotación Global", variant="h3"))
    
    # Query for Section 3: Global Snapshot with 3 rotation types
    # Single data point (current month) with 3 metrics
    comp_rot_req = {
        "intent": "SNAPSHOT",
        "cube_query": {
            "metrics": ["tasa_rotacion", "tasa_rotacion_voluntaria", "tasa_rotacion_involuntaria"],
            "dimensions": [],  # No dimensions = Global level
            "filters": base_filters
        },
        "metadata": {"requested_viz": "BAR_CHART"}
    }
    comp_rot_resp = execute_semantic_query(**comp_rot_req)
    
    # Extract values for the 3 metrics
    tasa_total = 0
    tasa_vol = 0
    tasa_invol = 0
    
    if comp_rot_resp.get("content"):
        first = comp_rot_resp["content"][0]
        payload = first.get("payload", {}) if isinstance(first, dict) else getattr(first, "payload", {})
        
        # Check if it's a KPI_ROW or raw data
        if "items" in payload:
            # KPI_ROW format
            items = payload.get("items", [])
            for item in items:
                label = item.get("label", "").lower() if isinstance(item, dict) else getattr(item, "label", "").lower()
                value = item.get("value", 0) if isinstance(item, dict) else getattr(item, "value", 0)
                
                if "total" in label or "global" in label or "rotación" in label and "voluntaria" not in label and "involuntaria" not in label:
                    tasa_total = float(value)
                elif "voluntaria" in label:
                    tasa_vol = float(value)
                elif "involuntaria" in label:
                    tasa_invol = float(value)
        elif "rows" in payload:
            # Table format (single row)
            rows = payload.get("rows", [])
            if rows:
                row = rows[0]
                tasa_total = float(row.get("tasa_rotacion", 0) if isinstance(row, dict) else getattr(row, "tasa_rotacion", 0))
                tasa_vol = float(row.get("tasa_rotacion_voluntaria", 0) if isinstance(row, dict) else getattr(row, "tasa_rotacion_voluntaria", 0))
                tasa_invol = float(row.get("tasa_rotacion_involuntaria", 0) if isinstance(row, dict) else getattr(row, "tasa_rotacion_involuntaria", 0))
    
    # Construct Grouped Bar Chart (3 bars, single category "Organización")
    comp_datasets = [
        Dataset(
            label="Rotación Total",
            data=[tasa_total],
            format=MetricFormat(unit_type="percentage", symbol="%", decimals=2),
            backgroundColor="#4361EE",
            borderColor="#4361EE"
        ),
        Dataset(
            label="Rotación Voluntaria",
            data=[tasa_vol],
            format=MetricFormat(unit_type="percentage", symbol="%", decimals=2),
            backgroundColor="#EF3340",
            borderColor="#EF3340"
        ),
        Dataset(
            label="Rotación Involuntaria",
            data=[tasa_invol],
            format=MetricFormat(unit_type="percentage", symbol="%", decimals=2),
            backgroundColor="#7209B7",
            borderColor="#7209B7"
        )
    ]
    
    # Add Grouped Bar Chart
    blocks.append(ChartBlock(
        subtype="BAR",
        payload=ChartPayload(
            labels=["Organización"],  # Single category
            datasets=comp_datasets
        ),
        metadata=ChartMetadata(
            title="Comparativa de Rotación Global",
            y_axis_label="Tasa de Rotación (%)",
            show_legend=True
        )
    ))

    # Optional: Keep table for detailed breakdown (can be removed if not needed)
    if top_5_voluntary:
        blocks.append(TextBlock(payload="3.1 Focos de Concentración (Divisiones Críticas)", variant="h4"))
        first = top_5_voluntary[0]
        headers = list(first.keys()) if isinstance(first, dict) else []
        safe_rows = [row if isinstance(row, dict) else row.__dict__ for row in top_5_voluntary]
        blocks.append(TableBlock(
            payload=TablePayload(headers=headers, rows=safe_rows)
        ))

    # [SECTION 4] Alerta de Talento Clave
    blocks.append(TextBlock(payload="4. Alerta de Talento Clave", variant="h3"))
    if hipers_list or hipos_list:
        all_leakage = hipers_list + hipos_list
        headers = ["nombre", "posicion", "uo2", "talento", "motivo"]
        clean_rows = []
        costo_total_est = 0
        for row in all_leakage:
            clean_row = {}
            src = row if isinstance(row, dict) else row.__dict__
            for h in headers:
                clean_row[h] = src.get(h, "")
            clean_rows.append(clean_row)
            # Simple simulation of cost impact (e.g. 6 salaries ~ 15k USD avg per talent)
            costo_total_est += 15000 

        blocks.append(TableBlock(
            payload=TablePayload(headers=headers, rows=clean_rows),
            metadata=ChartMetadata(title="Detalle de Fuga de Hipers/Hipos")
        ))
        
        # Detalle de Impacto (Calculated Insight)
        impact_msg = f"Detalle de Impacto: La salida de estos {len(all_leakage)} perfiles representa un costo estimado de reemplazo de ${costo_total_est:,.0f} USD y una pérdida significativa de curva de aprendizaje."
        blocks.append(TextBlock(payload=impact_msg, variant="insight", severity="warning"))

    # [SECTION 5] Tabla Comparativa Y Gráfico (vs. Promedio Anual)
    blocks.append(TextBlock(payload="5. Tabla Comparativa (vs. Promedio Anual)", variant="h3"))
    
    # 5.1 Add Line Chart (Monthly vs Average Line)
    # Reconstruct from captured YTD data
    if tasa_trends_data:
        # Use captured labels
        t_labels = trends_labels
        # Data Series 1: Actual Rate
        actual_data = tasa_trends_data
        # Data Series 2: Average Rate (Constant Line)
        # Calculate full year avg (or YTD avg)
        # Using `avg_rate` calculated earlier from YTD logic
        avg_line_data = [avg_rate] * len(t_labels)
        
        blocks.append(ChartBlock(
             subtype="LINE",
             payload=ChartPayload(
                 labels=t_labels,
                 datasets=[
                     Dataset(
                         label="Tasa Mensual (Real)", 
                         data=actual_data,
                         format=MetricFormat(unit_type="percentage", symbol="%", decimals=2),
                         borderColor="#4CAF50" # Green
                     ),
                     Dataset(
                         label=f"Promedio Anual ({avg_rate:.2f}%)", 
                         data=avg_line_data,
                         format=MetricFormat(unit_type="percentage", symbol="%", decimals=2),
                         borderColor="#9E9E9E" # Grey/Target
                         # dashed? Schema doesn't support dash style yet.
                     )
                 ]
             ),
             metadata=ChartMetadata(title="Comparativa: Real vs Promedio", y_axis_label="Tasa")
        ))
    
    # 5.2 Keep the Table
    if comp_rows:
        headers = ["Indicador", "Mes Actual", f"Promedio {parsed_period['display']}", "Variación"]
        blocks.append(TableBlock(
            payload=TablePayload(headers=headers, rows=comp_rows)
        ))

    # [SECTION 6 & 7] Placeholders for Narrative
    blocks.append(TextBlock(payload="6. Conclusión Estratégica", variant="h3"))
    blocks.append(TextBlock(payload="[Espacio reservado para conclusión generada por IA]", variant="standard"))
    
    blocks.append(TextBlock(payload="7. Recomendaciones", variant="h3"))
    blocks.append(TextBlock(payload="[Espacio reservado para recomendaciones generadas por IA]", variant="standard"))

    # Construct Final Package (Matches Standard Schema)
    pkg = VisualDataPackage(
        summary=f"Reporte Ejecutivo: {periodo_anomes} | Scope: {uo2_filter or 'Global'} | Generado: {datetime.now().strftime('%d/%m/%Y')}",
        content=blocks,
        response_type="visual_package"
    )
    
    logger.info("✅ [EXEC-REPORT] Reporte visual (v2) generado exitosamente.")
    return pkg.model_dump()
