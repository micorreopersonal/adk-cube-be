import asyncio
from typing import Dict, Any, Optional, Tuple
from app.services.bigquery import get_bq_service
from app.ai.utils.response_builder import ResponseBuilder
from app.core.config import get_settings
from datetime import datetime

# Importar constantes financieras para cálculos de impacto
# TODO: Importar desde BQ si es necesario, pero por ahora reusamos la logica de turnover.py si hiciera falta
# from app.ai.tools.bq_queries.turnover import _fetch_financial_params_bq

settings = get_settings()
bq_service = get_bq_service()
table_id = f"{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}"

def _safe_float(val: Any) -> float:
    """Convierte a float de manera segura, manejando None y NaN."""
    if val is None: return 0.0
    try:
        f = float(val)
        if f != f: return 0.0 # NaN check (NaN != NaN is True in Python)
        return f
    except (ValueError, TypeError):
        return 0.0

async def _fetch_benchmark_stats(year: int) -> Dict[str, float]:
    """Calcula stats promedio mensuales del año para comparativas."""
    query = f"""
    WITH MonthlyStats AS (
        SELECT 
            EXTRACT(MONTH FROM fecha_corte) as mes,
            COUNT(DISTINCT codigo_persona) as hc,
            (SELECT COUNT(*) FROM `{table_id}` WHERE EXTRACT(MONTH FROM fecha_cese) = EXTRACT(MONTH FROM t1.fecha_corte) AND EXTRACT(YEAR FROM fecha_cese) = {year}) as ceses
        FROM `{table_id}` t1
        WHERE EXTRACT(YEAR FROM fecha_corte) = {year} 
        AND estado = 'Activo'
        GROUP BY 1
    )
    SELECT 
        AVG(hc) as avg_hc,
        AVG(ceses) as avg_ceses,
        AVG(SAFE_DIVIDE(ceses, hc)) as avg_rate
    FROM MonthlyStats
    """
    df = bq_service.execute_query(query)
    if df.empty:
        return {"avg_hc": 0, "avg_ceses": 0, "avg_rate": 0}
    
    row = df.iloc[0]
    return {
        "avg_hc": float(row['avg_hc'] if row['avg_hc'] else 0),
        "avg_ceses": float(row['avg_ceses'] if row['avg_ceses'] else 0),
        "avg_rate": float(row['avg_rate'] if row['avg_rate'] else 0)
    }

async def _fetch_headline_stats(month: int, year: int) -> Dict[str, Any]:
    """Obtiene HC, Ceses y Tasas del mes especifico + Comparativa Mes Anterior."""
    # Lógica similar a get_monthly_attrition pero optimizada para el reporte
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    
    query = f"""
    WITH CurrentMonth AS (
        SELECT 
            (SELECT COUNT(DISTINCT codigo_persona) FROM `{table_id}` WHERE EXTRACT(YEAR FROM fecha_corte) = {prev_year} AND EXTRACT(MONTH FROM fecha_corte) = {prev_month} AND estado = 'Activo') as hc_inicial,
            (SELECT COUNT(*) FROM `{table_id}` WHERE EXTRACT(MONTH FROM fecha_cese) = {month} AND EXTRACT(YEAR FROM fecha_cese) = {year}) as total_cesados,
             (SELECT COUNT(*) FROM `{table_id}` WHERE EXTRACT(MONTH FROM fecha_cese) = {month} AND EXTRACT(YEAR FROM fecha_cese) = {year} AND UPPER(motivo_cese) = 'RENUNCIA') as total_renuncias
    )
    SELECT 
        hc_inicial, 
        total_cesados,
        total_renuncias,
        SAFE_DIVIDE(total_cesados, hc_inicial) as tasa_gral,
        SAFE_DIVIDE(total_renuncias, hc_inicial) as tasa_vol
    FROM CurrentMonth
    """
    df = bq_service.execute_query(query)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()

async def _fetch_segmentation(month: int, year: int) -> Dict[str, Any]:
    """Desglose ADMI vs FFVV."""
    query = f"""
    SELECT 
        CASE 
            WHEN segmento = 'EMPLEADO FFVV' THEN 'FFVV'
            WHEN segmento = 'PRACTICANTE' THEN 'PRACTICANTE'
            ELSE 'ADMI' 
        END as grupo,
        COUNT(*) as ceses
    FROM `{table_id}`
    WHERE EXTRACT(MONTH FROM fecha_cese) = {month}
    AND EXTRACT(YEAR FROM fecha_cese) = {year}
    GROUP BY 1
    """
    df = bq_service.execute_query(query)
    res = {"ADMI": 0, "FFVV": 0}
    for _, row in df.iterrows():
        if row['grupo'] in res:
            res[row['grupo']] = int(row['ceses'])
    return res

async def _fetch_key_talent_alerts(month: int, year: int) -> list:
    """Fuga de Hiper/High Potentials."""
    query = f"""
    SELECT nombre_completo, posicion, uo2 as division, mapeo_talento_ultimo_anio as valor
    FROM `{table_id}`
    WHERE EXTRACT(MONTH FROM fecha_cese) = {month} 
    AND EXTRACT(YEAR FROM fecha_cese) = {year}
    AND mapeo_talento_ultimo_anio IN (7, 8, 9)
    ORDER BY valor DESC
    """
    df = bq_service.execute_query(query)
    return df.to_dict(orient='records') 

def _generate_synthetic_insight(stats: Dict, segments: Dict, alerts: list, benchmark: Optional[Dict] = None) -> str:
    """
    Genera insight con comparativa clara respecto al Benchmark (Promedio Año Anterior).
    """
    rate = stats.get('rate_gral', stats.get('tasa_gral', 0))
    
    # 1. Nivel de Riesgo (Absoluto)
    nivel = "Estable"
    if rate > 0.03: nivel = "Crítico (Alto)"
    elif rate > 0.01: nivel = "Moderado"
    elif rate > 0.00: nivel = "Bajo"
    elif rate == 0.00: nivel = "Óptimo"

    # 2. Tendencia vs Benchmark
    trend_text = ""
    if benchmark and 'avg_rate' in benchmark:
        avg_prev = benchmark['avg_rate']
        diff = rate - avg_prev
        
        if abs(diff) < 0.001:
            trend_desc = "se mantiene en línea"
        elif diff > 0:
            trend_desc = "muestra una tendencia al alza"
        else:
            trend_desc = "muestra una tendencia a la baja"
            
        trend_text = f"{trend_desc} respecto al promedio del año anterior ({avg_prev:.2%})"

    # Determine focus
    admi = segments.get('ADMI', 0)
    ffvv = segments.get('FFVV', 0)
    total_seg = admi + ffvv
    
    if total_seg == 0:
        focus_text = "No hubo impacto en segmentos principales."
    else:
        focus = "Administrativos" if admi >= ffvv else "Fuerza de Ventas"
        count = admi if admi >= ffvv else ffvv
        focus_text = f"El impacto se concentra mayoritariamente en **{focus}** ({count} salidas)."
    
    txt = (
        f"La rotación del mes ({rate:.2%}) presenta un nivel **{nivel}** y {trend_text}. "
        f"{focus_text} "
    )
    if alerts:
        txt += f"🚨 **Alerta:** Se han detectado {len(alerts)} salidas de talento clave (Hiper/Hipo) que requieren atención inmediata."
        
    return txt

def generate_executive_report(
    month: Optional[int] = None, 
    year: Optional[int] = None, 
    uo_level: Optional[str] = "uo2",
    uo_value: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Genera el Reporte Ejecutivo Mensual o Anual con soporte de Dimensiones (UO).
    
    Args:
        month: Mes (1-12). Si es None, genera reporte anual.
        year: Año
        uo_level: Nivel organizacional ('uo2', 'uo3')
        uo_value: Nombre de la unidad (ej: 'DIVISION FINANZAS')
    """
    # Extraer parámetros de UO
    uo_level = uo_level or kwargs.get("uo_level") or kwargs.get("dimension")
    uo_value = uo_value or kwargs.get("uo_value") or kwargs.get("value")

    if not year:
        year = datetime.now().year
        
    if not month:
        return _generate_annual_report_sync(year, uo_level, uo_value)

    return _generate_monthly_report_sync(month, year, uo_level, uo_value)

def _get_dim_filter(uo_level: Optional[str], uo_value: Optional[str]) -> str:
    if uo_level and uo_value:
        return f"AND LOWER({uo_level.lower()}) LIKE '%{uo_value.lower()}%'"
    return ""

def _fetch_headline_stats_sync(month: int, year: int, uo_level: Optional[str], uo_value: Optional[str]) -> Dict[str, Any]:
    # Copia sincrona de la logica
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    dim_filter = _get_dim_filter(uo_level, uo_value)
    
    # HC Inicial (Mes Anterior)
    q_hc = f"""SELECT COUNT(DISTINCT codigo_persona) as hc FROM `{table_id}` 
               WHERE EXTRACT(YEAR FROM fecha_corte) = {prev_year} 
               AND EXTRACT(MONTH FROM fecha_corte) = {prev_month} 
               AND estado = 'Activo' AND segmento != 'PRACTICANTE' {dim_filter}"""
    df_hc = bq_service.execute_query(q_hc)
    hc = df_hc.iloc[0]['hc'] if not df_hc.empty else 0
    if hc == 0 and prev_year < 2022: hc = 2684 # Fallback historico

    # Ceses Mes
    q_ceses = f"""SELECT 
                    COUNT(*) as total,
                    COUNTIF(UPPER(motivo_cese) = 'RENUNCIA') as renuncias
                  FROM `{table_id}` 
                  WHERE EXTRACT(MONTH FROM fecha_cese) = {month} 
                  AND EXTRACT(YEAR FROM fecha_cese) = {year}
                  AND segmento != 'PRACTICANTE' {dim_filter}"""
    df_ceses = bq_service.execute_query(q_ceses)
    row_ceses = df_ceses.iloc[0] if not df_ceses.empty else {'total':0, 'renuncias':0}
    
    return {
        "hc": hc,
        "total_ceses": row_ceses['total'],
        "renuncias": row_ceses['renuncias'],
        "rate_gral": row_ceses['total']/hc if hc else 0,
        "rate_vol": row_ceses['renuncias']/hc if hc else 0
    }

def _fetch_top_divisions_sync(month: int, year: int, uo_level: Optional[str], uo_value: Optional[str]) -> list:
    """Top 3 Divisiones con mayor rotación voluntaria."""
    dim_filter = _get_dim_filter(uo_level, uo_value)
    # Si ya estamos filtrando por una división, bajamos a UO3 (Área)
    drill_col = "uo3" if uo_level == "uo2" else ("uo4" if uo_level == "uo3" else "uo2")
    
    query = f"""
    SELECT 
        {drill_col} as unidad,
        COUNT(*) as renuncias,
        (SELECT COUNT(DISTINCT codigo_persona) FROM `{table_id}` t2 
         WHERE t2.{drill_col} = t1.{drill_col} 
         AND EXTRACT(YEAR FROM fecha_corte) = {year} 
         AND EXTRACT(MONTH FROM fecha_corte) = {month}
         AND estado = 'Activo') as hc_div
    FROM `{table_id}` t1
    WHERE EXTRACT(MONTH FROM fecha_cese) = {month}
    AND EXTRACT(YEAR FROM fecha_cese) = {year}
    AND UPPER(motivo_cese) = 'RENUNCIA'
    {dim_filter}
    GROUP BY 1
    HAVING hc_div > 5
    ORDER BY renuncias DESC, hc_div ASC
    LIMIT 3
    """
    df = bq_service.execute_query(query)
    res = []
    for _, row in df.iterrows():
        rate = row['renuncias'] / row['hc_div'] if row['hc_div'] else 0
        res.append({
            "Unidad": row['unidad'],
            "Renuncias": int(row['renuncias']),
            "Tasa Vol": f"{rate:.1%}"
        })
    return res

def _fetch_segmentation_sync(month: int, year: int, uo_level: Optional[str], uo_value: Optional[str]) -> Dict[str, Any]:
    dim_filter = _get_dim_filter(uo_level, uo_value)
    query = f"""
    SELECT 
        CASE 
            WHEN segmento = 'EMPLEADO FFVV' THEN 'FFVV'
            ELSE 'ADMI' 
        END as grupo,
        COUNT(*) as ceses
    FROM `{table_id}`
    WHERE EXTRACT(MONTH FROM fecha_cese) = {month}
    AND EXTRACT(YEAR FROM fecha_cese) = {year}
    AND segmento != 'PRACTICANTE'
    {dim_filter}
    GROUP BY 1
    """
    df = bq_service.execute_query(query)
    res = {"ADMI": 0, "FFVV": 0}
    for _, row in df.iterrows():
        if row['grupo'] in res:
            res[row['grupo']] = int(row['ceses'])
    return res

def _fetch_benchmark_sync(year: int) -> Dict[str, float]:
    # Promedio del año (Benchmark)
    # Nota: Si estamos en feb, toma todo el año disponible (que puede ser solo enero/feb). 
    # Idealmente tomaria año anterior para benchmark estable, pero el spec dice "Promedio Año". 
    # Asumiremos Año Anterior (2024) como benchmark estable si year=2025.
    
    bench_year = year - 1
    query = f"""
    WITH MonthlyStats AS (
        SELECT 
            EXTRACT(MONTH FROM fecha_corte) as mes,
            COUNT(DISTINCT codigo_persona) as hc
        FROM `{table_id}`
        WHERE EXTRACT(YEAR FROM fecha_corte) = {bench_year} 
        AND estado = 'Activo' AND segmento != 'PRACTICANTE'
        GROUP BY 1
    ),
    MonthlyCeses AS (
         SELECT EXTRACT(MONTH FROM fecha_cese) as mes, COUNT(*) as ceses
         FROM `{table_id}` 
         WHERE EXTRACT(YEAR FROM fecha_cese) = {bench_year} AND segmento != 'PRACTICANTE'
         GROUP BY 1
    )
    SELECT 
        AVG(m.hc) as avg_hc,
        AVG(COALESCE(c.ceses,0)) as avg_ceses
    FROM MonthlyStats m
    LEFT JOIN MonthlyCeses c ON m.mes = c.mes
    """
    df = bq_service.execute_query(query)
    if df.empty: return {"avg_hc": 0, "avg_ceses": 0, "avg_rate": 0}
    
    row = df.iloc[0]
    avg_hc = _safe_float(row['avg_hc'])
    avg_ceses = _safe_float(row['avg_ceses'])
    return {
        "avg_hc": avg_hc,
        "avg_ceses": avg_ceses,
        "avg_rate": avg_ceses / avg_hc if avg_hc > 0 else 0
    }

def _fetch_alerts_sync(month: int, year: int, uo_level: Optional[str], uo_value: Optional[str]) -> list:
    dim_filter = _get_dim_filter(uo_level, uo_value)
    query = f"""
    SELECT nombre_completo, posicion, uo2 as division, mapeo_talento_ultimo_anio as valor
    FROM `{table_id}`
    WHERE EXTRACT(MONTH FROM fecha_cese) = {month} 
    AND EXTRACT(YEAR FROM fecha_cese) = {year}
    AND mapeo_talento_ultimo_anio IN (7, 8, 9)
    {dim_filter}
    ORDER BY valor DESC
    """
    df = bq_service.execute_query(query)
    return df.to_dict(orient='records')

def _generate_monthly_report_sync(month: int, year: int, uo_level: Optional[str], uo_value: Optional[str]) -> Dict[str, Any]:
    # 1. Gather Data with Dimension Support
    stats = _fetch_headline_stats_sync(month, year, uo_level, uo_value)
    segments = _fetch_segmentation_sync(month, year, uo_level, uo_value)
    benchmark = _fetch_benchmark_sync(year) # TODO: Add dimension to benchmark if needed
    alerts = _fetch_alerts_sync(month, year, uo_level, uo_value)
    top_divs = _fetch_top_divisions_sync(month, year, uo_level, uo_value)

    rb = ResponseBuilder()
    
    # 2. Insight (AI Generated - Mocked for MVP)
    insight = _generate_synthetic_insight(stats, segments, alerts, benchmark)
    
    # Header Reporte
    context_title = f"{uo_value}" if uo_value else "Corporativo"
    rb.add_text(f"### 📑 Reporte Ejecutivo: {context_title} ({month}/{year})", variant="standard")
    rb.add_insight_alert(insight, severity="info" if stats['rate_gral'] < 0.03 else "warning")
    
    # 3. Kpis Mes Actual Enriquecidos
    # 3. Kpis Mes Actual Enriquecidos
    hc_val = int(stats['hc'])
    ceses_total = int(stats['total_ceses'])
    voluntarios = int(stats['renuncias'])
    rate_gral = stats['rate_gral']
    involuntarios = ceses_total - voluntarios
    
    kpis = [
        {
            "label": "HC Base", 
            "value": str(hc_val), 
            "color": "blue",
            "tooltip_data": f"{hc_val} = Total Colaboradores Activos (Inicio de Mes)"
        },
        {
            "label": "Ceses Totales", 
            "value": str(ceses_total), 
            "delta": f"{ceses_total - int(benchmark['avg_ceses'])} vs Promedio ({int(benchmark['avg_ceses'])})", 
            "color": "red",
            "tooltip_data": f"{ceses_total} = {voluntarios} Renuncias + {involuntarios} Inv."
        },
        {
            "label": "Rotación General", 
            "value": f"{rate_gral:.2%}", 
            "color": "red" if rate_gral > benchmark['avg_rate'] else "green",
            "tooltip_data": f"{rate_gral:.2%} = ({ceses_total} Ceses / {hc_val} HC Base) * 100"
        },
        {
            "label": "Rotación Voluntaria",
            "value": f"{stats['rate_vol']:.2%}",
            "color": "orange",
            "tooltip_data": f"{stats['rate_vol']:.2%} = ({voluntarios} Renuncias / {hc_val} HC Base) * 100"
        }
    ]
    rb.add_kpi_row(kpis)
    
    # 4. Tabla Comparativa vs Benchmark (Año Anterior)
    comp_table = [
        {
            "Indicador": "Headcount Base", 
            "Mes Actual": str(int(stats['hc'])), 
            "Promedio Año Ant.": str(int(benchmark['avg_hc'])),
            "Variación": f"{(stats['hc'] - benchmark['avg_hc']) / benchmark['avg_hc']:.1%}" if benchmark['avg_hc'] else "N/A"
        },
        {
            "Indicador": "Ceses Totales", 
            "Mes Actual": str(int(stats['total_ceses'])), 
            "Promedio Año Ant.": str(int(benchmark['avg_ceses'])),
            "Variación": f"{(stats['total_ceses'] - benchmark['avg_ceses']) / benchmark['avg_ceses']:.1%}" if benchmark['avg_ceses'] else "N/A"
        },
        {
            "Indicador": "Tasa Rotación", 
            "Mes Actual": f"{stats['rate_gral']:.2%}", 
            "Promedio Año Ant.": f"{benchmark['avg_rate']:.2%}",
            "Variación": f"{(stats['rate_gral'] - benchmark['avg_rate'])*100:.2f} pp"
        }
    ]
    rb.add_text("#### 📊 Comparativa vs Promedio Año Anterior", variant="standard")
    rb.add_table(comp_table)
    
    # 5. Segmentación (Bar Chart simple data series manual or KPI)
    admi_share = segments['ADMI'] / stats['total_ceses'] if stats['total_ceses'] else 0
    ffvv_share = segments['FFVV'] / stats['total_ceses'] if stats['total_ceses'] else 0
    
    seg_kpis = [
        {
            "label": "Administrativos", 
            "value": f"{admi_share:.1%}", 
            "delta": f"{segments['ADMI']} ceses", 
            "color": "off",
            "tooltip_data": f"{admi_share:.1%} = ({segments['ADMI']} Adm. / {stats['total_ceses']} Total) * 100"
        },
        {
            "label": "Fuerza Ventas", 
            "value": f"{ffvv_share:.1%}", 
            "delta": f"{segments['FFVV']} ceses", 
            "color": "off",
            "tooltip_data": f"{ffvv_share:.1%} = ({segments['FFVV']} FFVV / {stats['total_ceses']} Total) * 100"
        }
    ]
    rb.add_text("#### 👥 Distribución por Segmento", variant="standard")
    rb.add_kpi_row(seg_kpis)
    
    # 3.1 Focos de Concentración (Lo insertamos aqui por flujo visual)
    if top_divs:
        rb.add_text("#### 🎯 3.1 Focos de Concentración (Top Divisiones con mayor Rotación Voluntaria)", variant="standard")
        rb.add_table(top_divs)

    # 6. Alertas Talento
    if alerts:
        rb.add_text("#### 🚨 Fugas de Talento Clave (Hiper/Hipo)", variant="standard")
        rb.add_table(alerts)
    else:
         rb.add_text("✅ No se registraron salidas de talento clave (Hiper/Hipo) en este periodo.", variant="insight", severity="info")
    
    # 7. Conclusión y Recomendaciones (Mocked)
    rb.add_text("#### 🧠 6. Conclusión Estratégica", variant="standard")
    rb.add_text("La rotación se mantiene dentro de los rangos esperados, aunque se observan focos específicos en áreas comerciales que requieren monitoreo. El impacto en talento clave ha sido contenido durante este periodo.", variant="standard")
    
    rb.add_text("#### 💡 7. Recomendaciones", variant="standard")
    recs = [
        "Realizar encuestas de salida profundas en las divisiones con mayor tasa voluntaria.",
        "Revisar competitividad salarial en posiciones críticas de Fuerza de Ventas.",
        "Reforzar planes de retención para High Potentials en áreas con tendencia al alza."
    ]
    rb.add_text("\n".join([f"- {r}" for r in recs]), variant="standard")

    return rb.to_dict()

def _fetch_headline_stats_annual_sync(year: int) -> Dict[str, Any]:
    """Calcula métricas acumuladas del AÑO completo."""
    # 1. HC Promedio del Año
    q_hc = f"""
    WITH MonthlyHC AS (
        SELECT EXTRACT(MONTH FROM fecha_corte) as mes, COUNT(DISTINCT codigo_persona) as hc
        FROM `{table_id}`
        WHERE EXTRACT(YEAR FROM fecha_corte) = {year} 
        AND estado = 'Activo' AND segmento != 'PRACTICANTE'
        GROUP BY 1
    )
    SELECT AVG(hc) as avg_hc FROM MonthlyHC
    """
    df_hc = bq_service.execute_query(q_hc)
    avg_hc = float(df_hc.iloc[0]['avg_hc']) if not df_hc.empty and df_hc.iloc[0]['avg_hc'] else 0
    if avg_hc == 0 and year < 2022: avg_hc = 2684 # Fallback

    # 2. Ceses Totales del Año
    q_ceses = f"""
    SELECT 
        COUNT(*) as total,
        COUNTIF(UPPER(motivo_cese) = 'RENUNCIA') as renuncias
    FROM `{table_id}` 
    WHERE EXTRACT(YEAR FROM fecha_cese) = {year}
    AND segmento != 'PRACTICANTE'
    """
    df_ceses = bq_service.execute_query(q_ceses)
    row_ceses = df_ceses.iloc[0] if not df_ceses.empty else {'total':0, 'renuncias':0}
    
    return {
        "avg_hc": avg_hc,
        "total_ceses": int(row_ceses['total']),
        "renuncias": int(row_ceses['renuncias']),
        "rate_annual": float(row_ceses['total'])/avg_hc if avg_hc else 0,
        "rate_vol_annual": float(row_ceses['renuncias'])/avg_hc if avg_hc else 0
    }

def _fetch_segmentation_sync_annual(year: int) -> Dict[str, Any]:
    query = f"""
    SELECT 
        CASE 
            WHEN segmento = 'EMPLEADO FFVV' THEN 'FFVV'
            ELSE 'ADMI' 
        END as grupo,
        COUNT(*) as ceses
    FROM `{table_id}`
    WHERE EXTRACT(YEAR FROM fecha_cese) = {year}
    AND segmento != 'PRACTICANTE'
    GROUP BY 1
    """
    df = bq_service.execute_query(query)
    res = {"ADMI": 0, "FFVV": 0}
    for _, row in df.iterrows():
        if row['grupo'] in res:
            res[row['grupo']] = int(row['ceses'])
    return res

def _fetch_alerts_sync_annual(year: int, uo_level: Optional[str], uo_value: Optional[str]) -> list:
    dim_filter = _get_dim_filter(uo_level, uo_value)
    query = f"""
    SELECT nombre_completo, posicion, uo2 as division, mapeo_talento_ultimo_anio as valor
    FROM `{table_id}`
    WHERE EXTRACT(YEAR FROM fecha_cese) = {year}
    AND mapeo_talento_ultimo_anio IN (7, 8, 9)
    {dim_filter}
    ORDER BY valor DESC
    LIMIT 10
    """
    df = bq_service.execute_query(query)
    return df.to_dict(orient='records')

def _fetch_top_divisions_sync_annual(year: int, uo_level: Optional[str], uo_value: Optional[str]) -> list:
    """Top 3 Unidades con mayor rotación voluntaria (Acumulado Anual)."""
    dim_filter = _get_dim_filter(uo_level, uo_value)
    drill_col = "uo3" if uo_level == "uo2" else ("uo4" if uo_level == "uo3" else "uo2")
    
    query = f"""
    SELECT 
        {drill_col} as unidad,
        COUNT(*) as renuncias,
        (SELECT COUNT(DISTINCT codigo_persona) FROM `{table_id}` t2 
         WHERE t2.{drill_col} = t1.{drill_col} 
         AND EXTRACT(YEAR FROM fecha_corte) = {year} 
         AND estado = 'Activo') as hc_div_anual
    FROM `{table_id}` t1
    WHERE EXTRACT(YEAR FROM fecha_cese) = {year}
    AND UPPER(motivo_cese) = 'RENUNCIA'
    {dim_filter}
    GROUP BY 1
    HAVING hc_div_anual > 5
    ORDER BY renuncias DESC
    LIMIT 3
    """
    df = bq_service.execute_query(query)
    res = []
    for _, row in df.iterrows():
        rate = row['renuncias'] / row['hc_div_anual'] if row['hc_div_anual'] else 0
        res.append({
            "Unidad": row['unidad'],
            "Renuncias": int(row['renuncias']),
            "Tasa Aprox": f"{rate:.1%}"
        })
    return res

def _generate_annual_report_sync(year: int, uo_level: Optional[str], uo_value: Optional[str]) -> Dict[str, Any]:
    # 1. Data Gathering
    stats_curr = _fetch_headline_stats_annual_sync(year) # TODO: Add dimension to headline if needed
    stats_prev = {"avg_hc": 0, "total_ceses": 0, "rate_annual": 0}
    try:
        stats_prev = _fetch_headline_stats_annual_sync(year - 1)
    except: pass

    segments = _fetch_segmentation_sync_annual(year) # TODO: Add dimension
    alerts = _fetch_alerts_sync_annual(year, uo_level, uo_value)
    top_divs = _fetch_top_divisions_sync_annual(year, uo_level, uo_value)

    rb = ResponseBuilder()
    
    # 2. Header
    rb.add_text(f"### 📅 Reporte Anual de Rotación: {year}", variant="standard")
    
    insight_text = (
        f"El año {year} cerró con una rotación acumulada del **{stats_curr['rate_annual']:.1%}** "
        f"({stats_curr['total_ceses']} salidas). "
    )
    if stats_prev['rate_annual'] > 0:
        delta = stats_curr['rate_annual'] - stats_prev['rate_annual']
        trend = "📈 Aumentó" if delta > 0 else "📉 Disminuyó"
        insight_text += f"Comparado con {year-1} ({stats_prev['rate_annual']:.1%}), la rotación {trend} en **{abs(delta)*100:.2f} pp**."
        
    rb.add_insight_alert(insight_text, severity="info")
    
    # 3. KPIs Anuales
    # 3. KPIs Anuales
    avg_hc_val = int(stats_curr['avg_hc'])
    ceses_total = int(stats_curr['total_ceses'])
    voluntarios = int(stats_curr['renuncias'])
    involuntarios = ceses_total - voluntarios
    rate_anual = stats_curr['rate_annual']
    
    kpis = [
        {
            "label": "HC Promedio", 
            "value": str(avg_hc_val), 
            "color": "blue",
            "tooltip_data": f"{avg_hc_val} = Promedio de los 12 cierres mensuales"
        },
        {
            "label": "Total Ceses", 
            "value": str(ceses_total), 
            "delta": f"vs {stats_prev['total_ceses']} en {year-1}", 
            "color": "red",
            "tooltip_data": f"{ceses_total} = {voluntarios} Renuncias + {involuntarios} Inv."
        },
        {
            "label": "Rotación General Anual", 
            "value": f"{rate_anual:.1%}", 
            "delta": f"vs {stats_prev['rate_annual']:.1%} en {year-1}", 
            "color": "red",
            "tooltip_data": f"{rate_anual:.1%} = ({ceses_total} Ceses / {avg_hc_val} Avg HC) * 100"
        },
        {
            "label": "Rotación Voluntaria",
            "value": f"{stats_curr['rate_vol_annual']:.2%}",
            "color": "orange",
            "tooltip_data": f"{stats_curr['rate_vol_annual']:.2%} = ({voluntarios} Renuncias / {avg_hc_val} Avg HC) * 100"
        }
    ]
    rb.add_kpi_row(kpis)
    
    # 4. Tabla Comparativa YoY (Year over Year)
    comp_table = [
        {
            "Indicador": "Headcount Promedio", 
            "Año Actual": str(int(stats_curr['avg_hc'])), 
            "Año Anterior": str(int(stats_prev['avg_hc'])),
            "Variación": f"{(stats_curr['avg_hc'] - stats_prev['avg_hc']) / stats_prev['avg_hc']:.1%}" if stats_prev['avg_hc'] else "N/A"
        },
        {
            "Indicador": "Ceses Totales", 
            "Año Actual": str(int(stats_curr['total_ceses'])), 
            "Año Anterior": str(int(stats_prev['total_ceses'])),
            "Variación": f"{(stats_curr['total_ceses'] - stats_prev['total_ceses']) / stats_prev['total_ceses']:.1%}" if stats_prev['total_ceses'] else "N/A"
        },
        {
            "Indicador": "Tasa Rotación", 
            "Año Actual": f"{stats_curr['rate_annual']:.1%}", 
            "Año Anterior": f"{stats_prev['rate_annual']:.1%}",
            "Variación": f"{(stats_curr['rate_annual'] - stats_prev['rate_annual'])*100:.2f} pp"
        }
    ]
    rb.add_text(f"#### 🆚 Comparativa Anual ({year} vs {year-1})", variant="standard")
    rb.add_table(comp_table)
    
    # 5. Distribución
    admi_share = segments['ADMI'] / stats_curr['total_ceses'] if stats_curr['total_ceses'] else 0
    ffvv_share = segments['FFVV'] / stats_curr['total_ceses'] if stats_curr['total_ceses'] else 0
    seg_kpis = [
        {
            "label": "Administrativos", 
            "value": f"{admi_share:.1%}", 
            "delta": f"{segments['ADMI']} ceses", 
            "color": "off",
            "tooltip_data": f"{admi_share:.1%} = ({segments['ADMI']} Adm. / {stats_curr['total_ceses']} Total) * 100"

        },
        {
            "label": "Fuerza Ventas", 
            "value": f"{ffvv_share:.1%}", 
            "delta": f"{segments['FFVV']} ceses", 
            "color": "off",
            "tooltip_data": f"{ffvv_share:.1%} = ({segments['FFVV']} FFVV / {stats_curr['total_ceses']} Total) * 100"
        }
    ]
    rb.add_text("#### 👥 Distribución del Año", variant="standard")
    rb.add_kpi_row(seg_kpis)

    # 3.1 Focos de Concentración (Anual)
    if top_divs:
        rb.add_text("#### 🎯 3.1 Focos de Concentración (Top Divisiones - Acumulado Anual)", variant="standard")
        rb.add_table(top_divs)

    # 6. Alertas Talento (Ya existía en data gathering pero faltaba en output anual anterior? No, estaba en data gathering)
    if alerts:
        rb.add_text("#### 🚨 Fugas de Talento Clave (Hiper/Hipo) - Acumulado", variant="standard")
        rb.add_table(alerts)
    else:
        rb.add_text("✅ No se registraron salidas de talento clave (Hiper/Hipo) en este periodo.", variant="insight", severity="info")

    # 7. Conclusión y Recomendaciones (Mocked)
    rb.add_text("#### 🧠 6. Conclusión Estratégica", variant="standard")
    rb.add_text(f"La rotación anual del {year} presenta desafíos estructurales. Se recomienda profundizar en las causas de salida en las áreas críticas.", variant="standard")
    
    rb.add_text("#### 💡 7. Recomendaciones", variant="standard")
    recs = [
        "Implementar dashboard de seguimiento mensual para líderes de Divisiones Foco.",
        "Revisar bandas salariales vs mercado (benchmarking) en Q1 del próximo año.",
        "Fortalecer programa de 'Onboarding' para reducir rotación temprana."
    ]
    rb.add_text("\n".join([f"- {r}" for r in recs]), variant="standard")
    
    return rb.to_dict()
