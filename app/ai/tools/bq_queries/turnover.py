import json
from typing import Dict, Any
from app.ai.utils.response_builder import ResponseBuilder

def get_turnover_deep_dive(
    parent_level: str = "UO2", 
    parent_value: str = "TOTAL", 
    periodo: str = "2025", 
    tipo_rotacion: str = "GENERAL",
    **kwargs
) -> Dict[str, Any]:
    """
    Realiza un análisis profundo de rotación (Hotspots) comparando sub-unidades contra su padre.
    
    Args:
        parent_level: 'UO2' (División), 'UO3' (Área) o 'UO4'.
        parent_value: Nombre de la unidad padre (ej: 'DIVISION FINANZAS'). 
        periodo: 'YYYY', 'YYYY-MM' o 'YYYY-QX'.
        tipo_rotacion: 'GENERAL' o 'VOLUNTARIA'.
    """
    from app.services.bigquery import get_bq_service
    from app.core.config import get_settings
    from app.ai.tools.bq_queries.financial_parameters import (
        AVG_ANNUAL_SALARY_USD, RECRUITMENT_COST_PCT, TRAINING_COST_USD,
        RAMP_UP_MONTHS, RAMP_UP_PRODUCTIVITY_FACTOR, SEVERANCE_AVG_USD
    )
    import pandas as pd

    settings = get_settings()
    bq_service = get_bq_service()
    builder = ResponseBuilder()
    table_id = f"{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}"

    # 1. Determinar Niveles
    level_map = {"UO2": ("uo2", "UO3"), "UO3": ("uo3", "UO4"), "UO4": ("uo4", "UO5")}
    parent_col, child_level_key = level_map.get(parent_level.upper(), ("uo2", "UO3"))
    child_col, _ = level_map.get(child_level_key, ("uo3", "UO4"))

    # 2. Configurar Filtros
    type_filter = "AND LOWER(motivo_cese) LIKE '%renuncia%'" if tipo_rotacion.upper() == "VOLUNTARIA" else ""
    
    # 2. Configurar Filtros de Fecha (Soporte para Año, Mes o Trimestre)
    def parse_periodo(p: str):
        # Trimestre (ej. "2025-Q1")
        if "-Q" in p.upper():
            year_str, q_str = p.upper().split("-Q")
            year = int(year_str)
            q_map = {
                "1": (1, 3), "2": (4, 6), "3": (7, 9), "4": (10, 12)
            }
            m_start, m_end = q_map.get(q_str, (1, 3))
            f_hc = f"EXTRACT(YEAR FROM fecha_corte) = {year} AND EXTRACT(MONTH FROM fecha_corte) = {m_start}"
            f_ceses = f"EXTRACT(YEAR FROM fecha_cese) = {year} AND EXTRACT(MONTH FROM fecha_cese) BETWEEN {m_start} AND {m_end}"
            label = f"Q{q_str} {year}"
            return f_hc, f_ceses, label

        # Mes específico (ej. "2025-12")
        elif len(p) == 7 and "-" in p:
            year, month = p.split("-")
            f_hc = f"EXTRACT(YEAR FROM fecha_corte) = {int(year)} AND EXTRACT(MONTH FROM fecha_corte) = {int(month)}"
            f_ceses = f"EXTRACT(YEAR FROM fecha_cese) = {int(year)} AND EXTRACT(MONTH FROM fecha_cese) = {int(month)}"
            return f_hc, f_ceses, p
        
        # Año completo (ej. "2025")
        else:
            year_val = int(p[:4])
            f_hc = f"EXTRACT(YEAR FROM fecha_corte) = {year_val} AND EXTRACT(MONTH FROM fecha_corte) = 1"
            f_ceses = f"EXTRACT(YEAR FROM fecha_cese) = {year_val}"
            return f_hc, f_ceses, str(year_val)

    date_filter_hc, date_filter_ceses, periodo_label = parse_periodo(periodo)
    
    dim_filter = f"AND LOWER({parent_col}) LIKE '%{parent_value.lower()}%'" if parent_value.upper() not in ["TOTAL", "GENERAL"] else ""

    # 3. Query de Hotspots (Detección de puntos críticos)
    query = f"""
    WITH 
    TotalBase AS (
        SELECT 
            COUNT(DISTINCT codigo_persona) as hc_inicial
        FROM `{table_id}`
        WHERE {date_filter_hc} AND estado = 'Activo' {dim_filter}
    ),
    TotalCeses AS (
        SELECT 
            COUNT(*) as ceses
        FROM `{table_id}`
        WHERE {date_filter_ceses}
        {dim_filter} {type_filter}
    ),
    Benchmark AS (
        SELECT SAFE_DIVIDE(c.ceses, NULLIF(b.hc_inicial, 0)) as tasa_parent
        FROM TotalCeses c, TotalBase b
    ),
    SubUnitsData AS (
        SELECT 
            {child_col} as unidad,
            COUNT(DISTINCT codigo_persona) as hc_child
        FROM `{table_id}`
        WHERE {date_filter_hc} AND estado = 'Activo' {dim_filter}
        GROUP BY 1
    ),
    SubUnitsCeses AS (
        SELECT 
            {child_col} as unidad,
            COUNT(*) as ceses_child
        FROM `{table_id}`
        WHERE {date_filter_ceses}
        {dim_filter} {type_filter}
        GROUP BY 1
    )
    SELECT 
        s.unidad,
        s.hc_child,
        COALESCE(c.ceses_child, 0) as ceses_child,
        SAFE_DIVIDE(COALESCE(c.ceses_child, 0), NULLIF(s.hc_child, 0)) as tasa_child,
        b.tasa_parent
    FROM SubUnitsData s
    LEFT JOIN SubUnitsCeses c ON s.unidad = c.unidad
    CROSS JOIN Benchmark b
    WHERE s.unidad IS NOT NULL
    ORDER BY tasa_child DESC
    """

    df = bq_service.execute_query(query)
    if df.empty:
        builder.add_text(f"No se encontró estructura organizacional para profundizar en {parent_value}.")
        return builder.to_dict()

    # 4. Cálculos Financieros y Hotspots
    tasa_parent = df['tasa_parent'].iloc[0] if not df.empty else 0
    hotspots = df[df['tasa_child'] > tasa_parent].copy()
    total_ceses = df['ceses_child'].sum()

    # Costo por salida
    cost_per_leaver = (AVG_ANNUAL_SALARY_USD * RECRUITMENT_COST_PCT) + TRAINING_COST_USD + \
                      (AVG_ANNUAL_SALARY_USD / 12 * RAMP_UP_MONTHS * (1 - RAMP_UP_PRODUCTIVITY_FACTOR)) + SEVERANCE_AVG_USD
    
    total_impact_usd = total_ceses * cost_per_leaver

    # 5. Construir Respuesta
    severity = "critical" if tasa_parent > 0.3 else "warning"
    insight = (
        f"Análisis organizacional de **{parent_value}** ({periodo_label}). "
        f"La tasa promedio de la unidad es **{tasa_parent:.2%}**. "
        f"Se identificaron **{len(hotspots)} áreas críticas** con rotación por encima del promedio divisional. "
        f"El impacto financiero estimado de estas salidas es de **${total_impact_usd / 1_000_000:.1f}M USD**."
    )
    
    builder.add_insight_alert(insight, severity=severity)
    
    # KPIs
    builder.add_kpi_row([
        {"label": f"Tasa {parent_value}", "value": f"{tasa_parent:.2%}", "color": "inverse"},
        {"label": "Áreas Críticas", "value": str(len(hotspots)), "color": "red" if len(hotspots) > 0 else "green"},
        {"label": "Impacto Económico", "value": f"${total_impact_usd/1e6:.1f}M", "color": "inverse"}
    ])

    # Gráfico de Hotspots
    chart_data = []
    # Mostramos los top 10 o todos si son menos
    display_df = df.head(10)
    for _, row in display_df.iterrows():
        is_hot = " (CRÍTICO)" if row['tasa_child'] > row['tasa_parent'] else ""
        chart_data.append({
            "label": f"{row['unidad']}{is_hot}",
            "value": round(row['tasa_child'] * 100, 2),
            "benchmark": round(row['tasa_parent'] * 100, 2),
            "hc": int(row['hc_child']),
            "ceses": int(row['ceses_child'])
        })

    builder.add_distribution_chart(
        chart_data, 
        title=f"Desglose por {child_level_key} en {parent_value}",
        chart_type="bar_chart",
        x_label=child_level_key,
        y_label="% Rotación"
    )

    # 5.4 Tabla de Datos (Visible para el Agente y opcional para UI)
    table_data = [
        {
            "Unidad": row['unidad'],
            "Headcount (Base)": int(row['hc_child']),
            "Ceses": int(row['ceses_child']),
            "Tasa %": f"{row['tasa_child']:.2%}"
        }
        for _, row in df.iterrows()
    ]
    builder.add_table(table_data)

    builder.add_debug_sql(query)
    return builder.to_dict()
