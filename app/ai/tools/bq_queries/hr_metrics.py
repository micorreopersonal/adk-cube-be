import json
from datetime import datetime
from typing import Optional, Dict, Any
from app.services.bigquery import get_bq_service
from app.core.config import get_settings
from app.ai.utils.response_builder import ResponseBuilder
import pandas as pd

settings = get_settings()
bq_service = get_bq_service()
table_id = f"{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}"

def _build_sql_filters(segmento: Optional[str], uo_level: Optional[str], uo_value: Optional[str]) -> tuple[str, str]:
    """
    Genera los fragmentos SQL para filtros de Segmento y Unidad Organizacional.
    Retorna: (segment_filter, dim_filter)
    """
    # 1. Filtro de segmento (Lógica Centralizada)
    segment_filter = "AND segmento != 'PRACTICANTE'" # Default
    if segmento:
        seg_clean = segmento.upper()
        if seg_clean == "FFVV":
            segment_filter = "AND segmento = 'EMPLEADO FFVV'"
        elif seg_clean in ["ADMINISTRATIVO", "ADMI"]:
            segment_filter = "AND segmento != 'EMPLEADO FFVV' AND segmento != 'PRACTICANTE'"

    # 2. Filtro de dimensión (UO)
    dim_filter = ""
    if uo_level and uo_value:
        # Sanitizar nivel de UO
        col_name = uo_level.lower() if uo_level else "uo2"
        # Prevenir inyección directa simple (aunque uo_value viene del LLM, idealmente se bindearía)
        dim_filter = f"AND LOWER({col_name}) LIKE '%{uo_value.lower()}%'"

    return segment_filter, dim_filter

def _fetch_yearly_series(year: int, segmento: Optional[str] = None, uo_level: Optional[str] = None, uo_value: Optional[str] = None) -> tuple[Dict[str, Any], str]:
    """Helper to fetch yearly trend data for visualizations with UO support."""
    
    segment_filter, dim_filter = _build_sql_filters(segmento, uo_level, uo_value)

    query = f"""
    WITH 
    MonthlyHC AS (
        SELECT 
            EXTRACT(MONTH FROM DATE_ADD(fecha_corte, INTERVAL 1 MONTH)) as mes,
            COUNT(DISTINCT codigo_persona) as hc_inicial
        FROM `{table_id}`
        WHERE EXTRACT(YEAR FROM fecha_corte) = {year}
        AND estado = 'Activo'
        {segment_filter} {dim_filter}
        GROUP BY 1
    ),
    MonthlyCeses AS (
        SELECT 
            EXTRACT(MONTH FROM fecha_cese) as mes,
            COUNT(*) as total_cesados,
            COUNTIF(UPPER(motivo_cese) LIKE '%RENUNCIA%') as cesados_voluntarios
        FROM `{table_id}`
        WHERE EXTRACT(YEAR FROM fecha_cese) = {year}
        {segment_filter} {dim_filter}
        GROUP BY 1
    )
    SELECT 
        COALESCE(hc.mes, c.mes) as mes,
        COALESCE(hc.hc_inicial, 0) as hc_inicial,
        COALESCE(c.total_cesados, 0) as total_cesados,
        COALESCE(c.cesados_voluntarios, 0) as cesados_voluntarios,
        SAFE_DIVIDE(COALESCE(c.total_cesados, 0), NULLIF(hc.hc_inicial, 0)) as tasa_general,
        SAFE_DIVIDE(COALESCE(c.cesados_voluntarios, 0), NULLIF(hc.hc_inicial, 0)) as tasa_voluntaria
    FROM MonthlyHC hc
    FULL OUTER JOIN MonthlyCeses c ON hc.mes = c.mes
    ORDER BY mes
    """
    
    df = bq_service.execute_query(query)
    
    if df.empty:
        return {}, query

    month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    months, rotacion_general, rotacion_voluntaria, rotacion_involuntaria = [], [], [], []
    headcount, ceses, renuncias, involuntarios = [], [], [], []
    
    for _, row in df.iterrows():
        mes_num = int(row['mes'])
        # Validar rango de mes
        if 1 <= mes_num <= 12:
            months.append(month_names[mes_num - 1])
            tasa_gen = float(row['tasa_general']) if pd.notna(row['tasa_general']) else 0.0
            tasa_vol = float(row['tasa_voluntaria']) if pd.notna(row['tasa_voluntaria']) else 0.0
            tasa_inv = tasa_gen - tasa_vol
            
            rotacion_general.append(round(tasa_gen * 100, 2))
            rotacion_voluntaria.append(round(tasa_vol * 100, 2))
            rotacion_involuntaria.append(round(tasa_inv * 100, 2))
            
            headcount.append(int(row['hc_inicial']))
            ces_tot = int(row['total_cesados'])
            ren_tot = int(row['cesados_voluntarios'])
            ceses.append(ces_tot)
            renuncias.append(ren_tot)
            involuntarios.append(ces_tot - ren_tot)
    
    return {
        "months": months,
        "rotacion_general": rotacion_general,
        "rotacion_voluntaria": rotacion_voluntaria,
        "rotacion_involuntaria": rotacion_involuntaria,
        "headcount": headcount,
        "ceses": ceses,
        "renuncias": renuncias,
        "involuntarios": involuntarios
    }, query


def get_monthly_attrition(
    month: int, 
    year: int, 
    segmento: Optional[str] = None, 
    uo_level: Optional[str] = "uo2",
    uo_value: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Calcula la tasa de rotación mensual con soporte de segmentación y dimensión UO.
    """
    # Extraer parámetros de UO (priorizando explicitos)
    uo_level = uo_level or kwargs.get("uo_level") or kwargs.get("dimension") or "uo2"
    uo_value = uo_value or kwargs.get("uo_value") or kwargs.get("value")

    # USAR HELPER DE FILTROS REFACTORIZADO
    segment_filter, dim_filter = _build_sql_filters(segmento, uo_level, uo_value)

    query = f"""
    WITH 
    HcInicial AS (
        SELECT COUNT(DISTINCT codigo_persona) as hc 
        FROM `{table_id}`
        WHERE EXTRACT(YEAR FROM fecha_corte) = {year if month > 1 else year - 1}
        AND EXTRACT(MONTH FROM fecha_corte) = {month - 1 if month > 1 else 12}
        AND estado = 'Activo'
        {segment_filter} {dim_filter}
    ),
    Cesados AS (
        SELECT 
            COUNT(*) as total_cesados,
            COUNTIF(UPPER(motivo_cese) LIKE '%RENUNCIA%') as cesados_voluntarios
        FROM `{table_id}`
        WHERE EXTRACT(MONTH FROM fecha_cese) = {month}
        AND EXTRACT(YEAR FROM fecha_cese) = {year}
        {segment_filter} {dim_filter}
    )
    SELECT 
        COALESCE(h.hc, 0) as hc_inicial,
        COALESCE(c.total_cesados, 0) as total_cesados,
        COALESCE(c.cesados_voluntarios, 0) as cesados_voluntarios,
        SAFE_DIVIDE(COALESCE(c.total_cesados, 0), NULLIF(h.hc, 0)) as tasa_rotacion_general,
        SAFE_DIVIDE(COALESCE(c.cesados_voluntarios, 0), NULLIF(h.hc, 0)) as tasa_rotacion_voluntaria
    FROM Cesados c
    CROSS JOIN HcInicial h
    """
    
    df = bq_service.execute_query(query)
    
    if df.empty:
        return ResponseBuilder().add_text(f"No se encontraron datos para {month}-{year}").to_dict()

    row = df.iloc[0]
    
    # Validación estricta: Si no hay HC inicial, advertir al usuario
    # EXCEPCIÓN: Para meses antes de Feb 2022, usar SALDOINICIAL (2684) como fallback
    if row['hc_inicial'] == 0:
        # Verificar si estamos en el rango sin data histórica (antes de Feb 2022)
        is_before_feb_2022 = (year == 2022 and month == 1) or (year < 2022)
        
        if is_before_feb_2022:
            # Usar SALDOINICIAL como fallback (coincide con DAX)
            hc_inicial_fallback = 2684
            rb = ResponseBuilder()
            rb.add_text(
                f"ℹ️ No hay datos del mes anterior para {month}/{year}. "
                f"Usando HC Inicial por defecto: {hc_inicial_fallback} (SALDOINICIAL).",
                variant="insight", severity="info"
            )
            # Recalcular tasas con el fallback
            rotacion_general = float(row['total_cesados']) / hc_inicial_fallback if hc_inicial_fallback > 0 else 0.0
            rotacion_voluntaria = float(row['cesados_voluntarios']) / hc_inicial_fallback if hc_inicial_fallback > 0 else 0.0
            
            # Construir respuesta con fallback
            kpis = [
                {
                    "label": "Rotación General",
                    "value": f"{rotacion_general:.2%}",
                    "delta": f"{row['total_cesados']} ceses",
                    "color": "red" if rotacion_general > 0.02 else "green"
                },
                {
                    "label": "Rotación Voluntaria",
                    "value": f"{rotacion_voluntaria:.2%}",
                    "delta": f"{row['cesados_voluntarios']} renuncias",
                    "tooltip_data": f"{rotacion_voluntaria:.2%} = ({int(row['cesados_voluntarios'])} Renuncias / {hc_inicial_fallback} HC Base) * 100",
                    "color": "orange" 
                },
                {
                    "label": "Headcount Base",
                    "value": str(hc_inicial_fallback),
                    "color": "blue"
                }
            ]
            rb.add_kpi_row(kpis)
            
            if rotacion_general > 0.0:
                rb.add_text(
                    f"En {month}/{year}, la rotación fue del {rotacion_general:.2%}, "
                    f"con {int(row['total_cesados'])} salidas totales sobre una base de {hc_inicial_fallback} colaboradores.",
                    variant="insight", severity="info"
                )
            
            rb.add_debug_sql(query)
            return rb.to_dict()
        else:
            # Para meses posteriores a Feb 2022, es un error real
            rb = ResponseBuilder()
            rb.add_text(
                f"⚠️ No se encontró headcount inicial para {month}/{year}. "
                f"Verifica que existan datos del mes anterior ({month-1 if month > 1 else 12}/{year if month > 1 else year-1}) en la tabla.",
                variant="insight", severity="warning"
            )
            rb.add_debug_sql(query)
            return rb.to_dict()

    row = df.iloc[0]
    
    # Sanitize inputs to avoid pandas.NA errors
    rotacion_general = float(row['tasa_rotacion_general']) if pd.notna(row['tasa_rotacion_general']) else 0.0
    rotacion_voluntaria = float(row['tasa_rotacion_voluntaria']) if pd.notna(row['tasa_rotacion_voluntaria']) else 0.0
    
    # Construir VisualDataPackage
    rb = ResponseBuilder()

    # --- Lógica de Etiquetado Dinámico ---
    segment_names = {
        "FFVV": "Fuerza de Ventas",
        "ADMINISTRATIVO": "Administrativa",
        "ADMI": "Administrativa"
    }
    
    # Determinar sufijo para títulos y textos
    if segmento:
        clean_seg = segmento.upper()
        seg_display = segment_names.get(clean_seg, clean_seg) 
        kpi_title = f"Rotación {seg_display}"
        text_context = f"la rotación de {seg_display}"
    else:
        kpi_title = "Rotación General"
        text_context = "la rotación general"
    
    # 1. KPIs Principales Enriquecidos
    kpis = [
        {
            "label": kpi_title,
            "value": f"{rotacion_general:.2%}",
            "delta": f"{row['total_cesados']} ceses (Base HC: {int(row['hc_inicial'])})",
            "tooltip_data": f"{rotacion_general:.2%} = ({int(row['total_cesados'])} Ceses / {int(row['hc_inicial'])} HC Base) * 100",
            "color": "red" if rotacion_general > 0.02 else "green"
        },
        {
            "label": "Rotación Voluntaria",
            "value": f"{rotacion_voluntaria:.2%}",
            "delta": f"{row['cesados_voluntarios']} renuncias",
            "tooltip_data": f"{rotacion_voluntaria:.2%} = ({int(row['cesados_voluntarios'])} Renuncias / {int(row['hc_inicial'])} HC Base) * 100",
            "color": "orange" 
        }
    ]
    rb.add_kpi_row(kpis)

    # 2. Insight Automático con Confirmación de Unidad
    context_unit = f"para **{uo_value}**" if uo_value else "a nivel **Corporativo**"
    
    if rotacion_general > 0.0:
        rb.add_text(
            f"En {month}/{year}, {text_context} {context_unit} fue del **{rotacion_general:.2%}**, "
            f"con {int(row['total_cesados'])} salidas totales sobre una base de {int(row['hc_inicial'])} colaboradores.",
            variant="insight", severity="info"
        )
    elif uo_value:
        rb.add_text(
            f"No se registraron salidas para **{uo_value}** en {month}/{year}. "
            f"La dotación base en este periodo fue de {int(row['hc_inicial'])} colaboradores.",
            variant="insight", severity="info"
        )

    # 3. Debug SQL
    rb.add_debug_sql(query)

    return rb.to_dict()

def get_talent_alerts(
    month: int, 
    year: int, 
    segmento: Optional[str] = None, 
    uo_level: Optional[str] = "uo2",
    uo_value: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Detecta fugas de talento clave (Hiper/Hipo) con soporte de UO.
    
    Args:
        month: Mes
        year: Año
        uo_level: Nivel organizacional ('uo2', 'uo3')
        uo_value: Nombre de la unidad
    """
    # Extraer parámetros de UO
    uo_level = uo_level or kwargs.get("uo_level") or kwargs.get("dimension")
    uo_value = uo_value or kwargs.get("uo_value") or kwargs.get("value")

    # Filtro de dimensión (UO)
    dim_filter = ""
    if uo_level and uo_value:
        dim_filter = f"AND LOWER({uo_level.lower()}) LIKE '%{uo_value.lower()}%'"

    query = f"""
    SELECT 
        nombre_completo,
        posicion,
        uo2 as division,
        motivo_cese,
        fecha_cese,
        mapeo_talento_ultimo_anio
    FROM `{table_id}`
    WHERE EXTRACT(MONTH FROM fecha_cese) = {month}
    AND EXTRACT(YEAR FROM fecha_cese) = {year}
    AND mapeo_talento_ultimo_anio IN (7, 8, 9)  -- Hipers (7) y Hipos (8,9)
    {dim_filter}
    ORDER BY mapeo_talento_ultimo_anio DESC, fecha_cese DESC
    """
    
    df = bq_service.execute_query(query)
    
    rb = ResponseBuilder()
    
    if df.empty:
        rb.add_text(
            f"✅ No se detectaron fugas de talento clave (Hiper/Hipo) en {month}/{year}.",
            variant="insight", severity="info"
        )
    else:
        count = len(df)
        rb.add_insight_alert(
            f"🚨 ALERTA: Se detectaron {count} salidas de talento clave en {month}/{year}. Revisar inmediatamente.",
            severity="critical"
        )
        
        records = df.to_dict(orient='records')
        rb.add_table(records)

    rb.add_debug_sql(query)
    return rb.to_dict()

def get_yearly_attrition(
    year: int, 
    segmento: Optional[str] = None, 
    uo_level: Optional[str] = "uo2",
    uo_value: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Calcula la rotación anual con soporte de segmentación y dimensión UO.
    
    Args:
        year: Año
        segmento: 'FFVV', 'ADMI' o 'TOTAL'
        uo_level: Nivel organizacional ('uo2', 'uo3')
        uo_value: Nombre de la unidad
    """
    # Extraer parámetros de UO
    uo_level = uo_level or kwargs.get("uo_level") or kwargs.get("dimension")
    uo_value = uo_value or kwargs.get("uo_value") or kwargs.get("value")

    # USAR HELPER DE FILTROS REFACTORIZADO
    segment_filter, dim_filter = _build_sql_filters(segmento, uo_level, uo_value)

    query = f"""
    WITH 
    MonthlyHC AS (
        SELECT 
            EXTRACT(MONTH FROM fecha_corte) as mes,
            COUNT(DISTINCT codigo_persona) as hc
        FROM `{table_id}`
        WHERE EXTRACT(YEAR FROM fecha_corte) = {year}
        AND estado = 'Activo'
        {segment_filter} {dim_filter}
        GROUP BY 1
    ),
    AnnualStats AS (
        SELECT 
            AVG(hc) as avg_hc,
            (SELECT COUNT(DISTINCT nombre_completo) 
             FROM `{table_id}` 
             WHERE EXTRACT(YEAR FROM fecha_cese) = {year}
             {segment_filter} {dim_filter}
            ) as total_cesados,
            (SELECT COUNT(DISTINCT CASE WHEN UPPER(motivo_cese) LIKE '%RENUNCIA%' THEN nombre_completo END)
             FROM `{table_id}` 
             WHERE EXTRACT(YEAR FROM fecha_cese) = {year}
             {segment_filter} {dim_filter}
            ) as total_renuncias
        FROM MonthlyHC
    )
    SELECT 
        avg_hc,
        total_cesados,
        total_renuncias,
        SAFE_DIVIDE(total_cesados, avg_hc) as tasa_anual,
        SAFE_DIVIDE(total_renuncias, avg_hc) as tasa_voluntaria_anual
    FROM AnnualStats
    """
    
    df = bq_service.execute_query(query)
    
    if df.empty:
        return ResponseBuilder().add_text(f"No se encontró información para el año {year}").to_dict()

    row = df.iloc[0]
    
    # Sanitize inputs
    tasa_anual = float(row['tasa_anual']) if pd.notna(row['tasa_anual']) else 0.0
    tasa_voluntaria = float(row['tasa_voluntaria_anual']) if pd.notna(row['tasa_voluntaria_anual']) else 0.0
    avg_hc = int(row['avg_hc']) if pd.notna(row['avg_hc']) else 0
    total_cesados = int(row['total_cesados']) if pd.notna(row['total_cesados']) else 0
    total_renuncias = int(row['total_renuncias']) if pd.notna(row['total_renuncias']) else 0

    rb = ResponseBuilder()

    # 1. KPIs Anuales Enriquecidos
    # 1. KPIs Anuales Enriquecidos
    # Nota: tasa_anual viene de database como decimal (0.1557), total_cesados y avg_hc son enteros
    kpis = [
        {
            "label": f"Rotación Anual {year}",
            "value": f"{tasa_anual:.2%}",
            "delta": f"{total_cesados} ceses (Avg HC: {avg_hc})",
            "tooltip_data": f"{tasa_anual:.2%} = ({total_cesados} Ceses / {avg_hc} Avg HC) * 100",
            "color": "red" if tasa_anual > 0.15 else "green" 
        },
        {
            "label": f"Voluntaria {year}",
            "value": f"{tasa_voluntaria:.2%}",
            "delta": f"{total_renuncias} renuncias",
            "tooltip_data": f"{tasa_voluntaria:.2%} = ({total_renuncias} Renuncias / {avg_hc} Avg HC) * 100",
            "color": "orange" 
        }
    ]
    rb.add_kpi_row(kpis)
    
    context_unit = f"para **{uo_value}**" if uo_value else "a nivel **Corporativo**"
    
    # Inyectar Título de Sección (Mejora UX)
    rb.add_text(f"### 📅 Balance Anual {year}", variant="standard")

    rb.add_text(
        f"Al cierre del {year}, el desempeño de retención {context_unit} refleja una tasa anual del **{tasa_anual:.2%}**, lo que representa {total_cesados} salidas totales. "
        f"La estructura base se mantuvo estable con un promedio de {avg_hc} colaboradores.",
        variant="insight"
    )

    # 2. Contexto Anual (Data Series) con soporte de UO
    series_data, series_query = _fetch_yearly_series(year, segmento, uo_level=uo_level, uo_value=uo_value)
    if series_data:
        rb.add_data_series(series_data, metadata={
            "year": year, 
            "segmento": segmento or "TOTAL",
            "uo_level": uo_level,
            "uo_value": uo_value
        })

    # 3. Debug SQL (Incluye ambas queries)
    rb.add_debug_sql(f"-- Query Anual KPI:\n{query}\n\n-- Query Tendencia Mensual:\n{series_query}")

    return rb.to_dict()

def get_monthly_trend(
    year: int, 
    year_comparison: Optional[int] = None, # Nuevo parámetro de comparación
    segmento: Optional[str] = None,
    month_start: int = 1,
    month_end: int = 12,
    uo_level: Optional[str] = "uo2",
    uo_value: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Obtiene la tendencia mensual de rotación con soporte de dimensiones y COMPARACIÓN MULTIANUAL.
    
    Args:
        year: Año principal a analizar
        year_comparison: (Opcional) Segundo año para contrastar (ej. 2024 vs 2025)
        segmento: Segmento opcional ('FFVV', 'ADMI')
        month_start: Mes inicio
        month_end: Mes fin
        uo_level: Nivel organizacional ('uo2', 'uo3')
        uo_value: Nombre de la unidad
    """
    # Validar consistencia básica
    if month_start < 1: month_start = 1
    if month_end > 12: month_end = 12
    if month_start > month_end: month_start, month_end = 1, 12

    # Extraer parámetros de UO
    uo_level = uo_level or kwargs.get("uo_level") or kwargs.get("dimension") or "uo2"
    uo_value = uo_value or kwargs.get("uo_value") or kwargs.get("value")

    # ---------------------------------------------------------
    # 1. Fetch de datos PRINCIPALES (Año 1)
    # ---------------------------------------------------------
    full_data_y1, query_y1 = _fetch_yearly_series(year, segmento, uo_level=uo_level, uo_value=uo_value)
    
    if not full_data_y1 or not full_data_y1.get("months"):
        # Si no hay datos del año principal, retornamos msj de error
        return ResponseBuilder().add_text(f"No se encontraron datos para el año {year}").to_dict()

    # ---------------------------------------------------------
    # 2. Fetch de datos COMPARATIVOS (Año 2, Opcional)
    # ---------------------------------------------------------
    full_data_y2 = {}
    query_y2 = ""
    is_comparison = False
    
    if year_comparison and year_comparison != year:
        full_data_y2, query_y2 = _fetch_yearly_series(year_comparison, segmento, uo_level=uo_level, uo_value=uo_value)
        if full_data_y2 and full_data_y2.get("months"):
            is_comparison = True

    # ---------------------------------------------------------
    # 3. Lógica de Filtrado y Fusión (HU-007 + Comparativo)
    # ---------------------------------------------------------
    mes_map = {"Ene":1, "Feb":2, "Mar":3, "Abr":4, "May":5, "Jun":6, 
               "Jul":7, "Ago":8, "Sep":9, "Oct":10, "Nov":11, "Dic":12}
    
    # Preparamos las listas finales
    final_months = []
    final_series_y1 = [] # Datos año principal
    final_series_y1_vol = [] # Datos voluntaria año principal
    final_series_y1_inv = [] # Datos involuntaria año principal
    final_series_y2 = [] # Datos año comparativo (si aplica)
    final_series_y2_vol = [] # Datos voluntaria año comparativo
    final_series_y2_inv = [] # Datos involuntaria año comparativo
    
    final_ceses_y1 = [] 
    final_hc_y1 = []
    final_renuncias_y1 = []
    final_involuntarios_y1 = []
    
    # Iteramos sobre los 12 meses ideales para alinear
    # (Asumimos _fetch_yearly_series devuelve meses ordenados, pero puede saltarse algunos si no hay datos)
    # Estrategia: Crear dict lookup para acceso rápido
    
    def series_to_lookup(s_data):
        if not s_data: return {}
        # Mapea MesNombre -> indice en arrays originales
        return {m: i for i, m in enumerate(s_data.get("months", []))}

    lookup_y1 = series_to_lookup(full_data_y1)
    lookup_y2 = series_to_lookup(full_data_y2)
    
    month_names_ordered = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    for i, m_name in enumerate(month_names_ordered):
        m_num = i + 1
        
        # Filtro de rango de meses
        if month_start <= m_num <= month_end:
            
            # Chequear si existe dato en Y1
            idx_y1 = lookup_y1.get(m_name)
            val_y1 = full_data_y1["rotacion_general"][idx_y1] if idx_y1 is not None else None
            
            # Chequear si existe dato en Y2
            idx_y2 = lookup_y2.get(m_name)
            val_y2 = full_data_y2["rotacion_general"][idx_y2] if idx_y2 is not None else None
            
            # Si hay datos de Y1 (o si queremos forzar el eje aunque sea Nulo), agregamos
            # En comparaciones, idealmente mostramos el mes si al menos UNO de los dos años tiene data
            if val_y1 is not None or (is_comparison and val_y2 is not None):
                final_months.append(m_name)
                
                # Datos Y1
                final_series_y1.append(val_y1 if val_y1 is not None else 0.0)
                # Voluntaria Y1
                val_y1_vol = full_data_y1["rotacion_voluntaria"][idx_y1] if idx_y1 is not None else 0.0
                final_series_y1_vol.append(val_y1_vol)
                # Involuntaria Y1
                val_y1_inv = full_data_y1["rotacion_involuntaria"][idx_y1] if idx_y1 is not None else 0.0
                final_series_y1_inv.append(val_y1_inv)

                if idx_y1 is not None:
                    final_ceses_y1.append(full_data_y1["ceses"][idx_y1])
                    final_hc_y1.append(full_data_y1["headcount"][idx_y1])
                    # Renuncias Raw (para Tooltips/Tabla)
                    final_renuncias_y1.append(full_data_y1["renuncias"][idx_y1] if "renuncias" in full_data_y1 else 0)
                    final_involuntarios_y1.append(full_data_y1["involuntarios"][idx_y1] if "involuntarios" in full_data_y1 else 0)
                else:
                    final_ceses_y1.append(0)
                    final_hc_y1.append(0)
                    final_renuncias_y1.append(0)
                    final_involuntarios_y1.append(0)

                # Datos Y2
                if is_comparison:
                    final_series_y2.append(val_y2 if val_y2 is not None else 0.0)
                    # Voluntaria Y2
                    val_y2_vol = full_data_y2["rotacion_voluntaria"][idx_y2] if idx_y2 is not None else 0.0
                    final_series_y2_vol.append(val_y2_vol)
                    # Involuntaria Y2
                    val_y2_inv = full_data_y2["rotacion_involuntaria"][idx_y2] if idx_y2 is not None else 0.0
                    final_series_y2_inv.append(val_y2_inv)

    if not final_months:
        context_unit = f"para **{uo_value}**" if uo_value else ""
        return ResponseBuilder().add_text(
            f"No se encontraron datos registrados {context_unit} en el rango seleccionado."
        ).to_dict()

    # ---------------------------------------------------------
    # 4. Cálculo de KPIs (Solo sobre Año Principal Y1)
    # ---------------------------------------------------------
    # Nota: Los KPIs de cards siguen enfocados en el año "principal" solicitado por el usuario.
    # El review comparativo se ve en el gráfico.
    
    avg_rotacion = sum(final_series_y1) / len(final_series_y1) if final_series_y1 else 0.0
    total_ceses = sum(final_ceses_y1)
    avg_hc = int(sum(final_hc_y1) / len(final_hc_y1)) if final_hc_y1 else 0
    tooltip_avg = f"{total_ceses} Ceses / {avg_hc} HC Promedio"

    # Max / Min Y1
    max_rotacion = max(final_series_y1) if final_series_y1 else 0.0
    min_rotacion = min(final_series_y1) if final_series_y1 else 0.0
    
    # Tooltips Max/Min Y1
    def get_tooltip_point(val, series, m_list, c_list, h_list):
        if not series: return "Sin datos"
        try:
            idx = series.index(val)
            return f"{val:.2f}% = ({c_list[idx]} Ceses / {h_list[idx]} HC) [{m_list[idx]}]"
        except: return "Sin datos"

    tooltip_max = get_tooltip_point(max_rotacion, final_series_y1, final_months, final_ceses_y1, final_hc_y1)
    tooltip_min = get_tooltip_point(min_rotacion, final_series_y1, final_months, final_ceses_y1, final_hc_y1)

    rb = ResponseBuilder()

    # Card KPIs
    label_periodo = f"Promedio {year}"
    
    # Tooltip Formulas (Actual Values)
    sum_tasas = sum(final_series_y1)
    count_meses = len(final_series_y1)
    formula_tooltip = f"{avg_rotacion:.2f}% = Suma Tasas({sum_tasas:.1f}%) / {count_meses} Meses"
    
    # Deltas
    delta_avg = "Promedio Anual"
    delta_max = f"Pico Anual {year}"
    delta_min = f"Mínimo Anual {year}"

    if is_comparison: 
        label_periodo += f" (Vs {year_comparison})"
        
        # Calcular stats Y2 (Comparativo)
        def calc_safe_stats(series):
            if not series: return 0.0, 0.0, 0.0
            return (
                sum(series)/len(series), 
                max(series), 
                min(series)
            )

        avg_y2, max_y2, min_y2 = calc_safe_stats(final_series_y2)
        
        delta_avg = f"vs {avg_y2:.2f}% en {year_comparison}"
        delta_max = f"vs max {max_y2:.2f}% en {year_comparison}"
        delta_min = f"vs min {min_y2:.2f}% en {year_comparison}"

    
    kpis = [
        { "label": label_periodo, "value": f"{avg_rotacion:.2f}%", "delta": delta_avg, "tooltip_data": formula_tooltip, "color": "blue" },
        { "label": f"Máximo {year}", "value": f"{max_rotacion:.2f}%", "delta": delta_max, "tooltip_data": tooltip_max, "color": "red" },
        { "label": f"Mínimo {year}", "value": f"{min_rotacion:.2f}%", "delta": delta_min, "tooltip_data": tooltip_min, "color": "green" }
    ]
    rb.add_kpi_row(kpis)

    # ---------------------------------------------------------
    # 5. Textos y Títulos
    # ---------------------------------------------------------
    context_unit = f"para **{uo_value}**" if uo_value else "a nivel **Corporativo**"
    seg_names = {"FFVV": "Fuerza de Ventas", "ADMI": "Administrativa", "ADMINISTRATIVO": "Administrativa"}
    context_seg = f" del segmento **{seg_names.get(segmento.upper(), segmento)}**" if segmento else ""
    
    range_text = f"entre los meses {month_start} y {month_end}" if (month_start > 1 or month_end < 12) else "durante todo el periodo"

    title_icon = "📈" if not is_comparison else "📊"
    title_main = f"{title_icon} Dinámica Mensual de Rotación {year}"
    if is_comparison: title_main += f" vs {year_comparison}"
    
    rb.add_text(f"### {title_main}", variant="standard")
    
    if is_comparison:
        rb.add_text(
            f"Analizando la evolución comparativa {year} vs {year_comparison} {context_unit}{context_seg}. "
            "El gráfico resalta las diferencias estacionales entre ambos periodos:",
            variant="standard"
        )
    else:
        rb.add_text(
            f"Analizando la tendencia {range_text} de {year}, observamos el comportamiento {context_unit}{context_seg}.",
            variant="standard"
        )

    # ---------------------------------------------------------
    # 6. Construcción del Payload Gráfico (Multi-Serie)
    # ---------------------------------------------------------
    # El Frontend espera: { "months": [...], "rotacion_general": [...] } simple OR
    # { "months": [...], "2024": [...], "2025": [...] } para multi-serie.
    
    chart_payload = {
        "months": final_months,
        str(year): final_series_y1
    }
    
    if is_comparison:
        # Agregamos la segunda serie
        chart_payload[str(year_comparison)] = final_series_y2
        
        # Agregamos series de Voluntaria para AMBOS años
        chart_payload[f"{year} Voluntaria"] = final_series_y1_vol
        chart_payload[f"{year_comparison} Voluntaria"] = final_series_y2_vol

        # Agregamos series de Involuntaria para AMBOS años
        chart_payload[f"{year} Involuntaria"] = final_series_y1_inv
        chart_payload[f"{year_comparison} Involuntaria"] = final_series_y2_inv
        
        # Metadata para que el frontend sepa que es comparativo
        meta = {
            "type": "comparison",
            "primary_year": year,
            "secondary_year": year_comparison,
            "segmento": segmento or "TOTAL"
        }
        
        # COMPATIBILIDAD FRONTEND: Llenar keys standard con datos del año principal (Y1)
        # Esto previene el error "ValueError: All arrays must be of the same length"
        chart_payload["rotacion_general"] = final_series_y1
        chart_payload["rotacion_voluntaria"] = final_series_y1_vol
        chart_payload["headcount"] = final_hc_y1
        chart_payload["ceses"] = final_ceses_y1
        chart_payload["renuncias"] = final_renuncias_y1
    else:
        # Modo simple (Legacy compatible)
        # Mantenemos keys standard para no romper charts viejos si el frontend espera 'rotacion_general'
        chart_payload["rotacion_general"] = final_series_y1
        chart_payload["rotacion_voluntaria"] = final_series_y1_vol
        chart_payload["rotacion_involuntaria"] = final_series_y1_inv
        chart_payload["headcount"] = final_hc_y1
        chart_payload["ceses"] = final_ceses_y1
        chart_payload["renuncias"] = final_renuncias_y1
        chart_payload["involuntarios"] = final_involuntarios_y1
        meta = {"year": year, "segmento": segmento or "TOTAL"}

    rb.add_data_series(chart_payload, metadata=meta)
    
    # 7. Debug SQL
    debug_q = f"-- YEAR {year}:\n{query_y1}"
    if is_comparison: debug_q += f"\n\n-- YEAR {year_comparison}:\n{query_y2}"
    rb.add_debug_sql(debug_q)
    
    return rb.to_dict()

def get_headcount_stats(
    periodo: str = "2025", 
    uo_level: Optional[str] = None, 
    uo_value: Optional[str] = None, 
    **kwargs
) -> Dict[str, Any]:
    """
    Obtiene un snapshot de la población activa (Headcount).
    Soporta formatos: '2025', '2025-01', '2025-Q1'..'2025-Q4'.
    """
    rb = ResponseBuilder()
    
    # Reutilizar lógica de parsing de trimestres/fechas
    def parse_periodo_hc(p: str):
        if "-Q" in p.upper():
            year_str, q_str = p.upper().split("-Q")
            q_map = {"1": 1, "2": 4, "3": 7, "4": 10}
            m = q_map.get(q_str, 1)
            f = f"EXTRACT(YEAR FROM fecha_corte) = {int(year_str)} AND EXTRACT(MONTH FROM fecha_corte) = {m}"
            l = f"Q{q_str} {year_str}"
            return f, l
        elif len(p) == 7 and "-" in p:
            year, month = p.split("-")
            f = f"EXTRACT(YEAR FROM fecha_corte) = {int(year)} AND EXTRACT(MONTH FROM fecha_corte) = {int(month)}"
            return f, p
        else:
            year_val = int(p[:4])
            # Para el año, mostramos el HC al inicio del año (o último disponible)
            f = f"EXTRACT(YEAR FROM fecha_corte) = {year_val} AND EXTRACT(MONTH FROM fecha_corte) = 1"
            return f, str(year_val)

    date_filter, periodo_label = parse_periodo_hc(periodo)
    
    # Filtro de unidad
    dim_filter = ""
    if uo_level and uo_value:
        col = uo_level.lower()
        dim_filter = f"AND LOWER({col}) LIKE '%{uo_value.lower()}%'"

    # Determinar nivel de desglose
    child_level = "uo2" if not uo_level else ("uo3" if uo_level.lower() == "uo2" else "uo4")
    
    query = f"""
    SELECT 
        {child_level} as unidad,
        COUNT(DISTINCT codigo_persona) as hc
    FROM `{table_id}`
    WHERE {date_filter}
    AND estado = 'Activo'
    AND segmento != 'PRACTICANTE'
    {dim_filter}
    GROUP BY 1
    ORDER BY hc DESC
    """
    
    df = bq_service.execute_query(query)
    
    if df.empty:
        return rb.add_text(f"No se encontró información de población para {periodo_label}").to_dict()

    total_hc = int(df['hc'].sum())
    
    # 1. KPI Principal
    rb.add_kpi_row([
        {
            "label": f"Headcount Total ({periodo_label})",
            "value": f"{total_hc:,}",
            "delta": uo_value if uo_value else "Corporativo",
            "tooltip_data": f"{total_hc:,} = Total Colaboradores Activos Activos",
            "color": "blue"
        }
    ])
    
    # 2. Resumen
    rb.add_text(
        f"Al cierre de **{periodo_label}**, la población activa calculada para **{uo_value or 'la organización'}** es de **{total_hc:,} colaboradores** (excluyendo practicantes).",
        variant="insight"
    )
    
    # 3. Desglose en Tabla
    table_data = df.to_dict(orient='records')
    rb.add_table(table_data)
    
    # 4. Gráfico de Distribución
    chart_data = [
        {"label": str(row['unidad']), "value": int(row['hc'])}
        for _, row in df.iterrows()
    ]
    rb.add_distribution_chart(
        data=chart_data,
        title=f"Distribución de Headcount por {child_level.upper()}",
        chart_type="bar",
        x_label=child_level.upper(),
        y_label="Colaboradores"
    )
    
    rb.add_debug_sql(query)
    return rb.to_dict()

def get_year_comparison_trend(
    year_current: int,
    year_previous: int,
    segmento: Optional[str] = None,
    month_start: int = 1,
    month_end: int = 12,
    uo_level: Optional[str] = "uo2",
    uo_value: Optional[str] = None,
) -> Dict[str, Any]:
    """
    GENERA UN GRÁFICO COMPARATIVO FLEXIBLE entre periodos de dos años.
    Soporta años completos, trimestres (Quarters), meses sueltos o rangos personalizados.
    
    Args:
        year_current: El año más reciente (ej. 2025).
        year_previous: El año contra el cual comparar (ej. 2024).
        segmento: Filtro opcional ('FFVV', 'ADMI').
        month_start: Mes inicial del rango (1-12). Ej: 1 para Q1, 3 para Mar-Jul.
        month_end: Mes final del rango (1-12). Ej: 3 para Q1, 7 para Mar-Jul.
        uo_level: 'uo2' o 'uo3'.
        uo_value: Nombre de la unidad.
        
    Ejemplos:
    - Año completo: start=1, end=12
    - Q4 2024 vs 2025: start=10, end=12
    - Dic 24 vs Dic 25: start=12, end=12
    """
    return get_monthly_trend(
        year=year_current,
        year_comparison=year_previous,
        segmento=segmento,
        month_start=month_start,
        month_end=month_end,
        uo_level=uo_level,
        uo_value=uo_value
    )
