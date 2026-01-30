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

def _fetch_yearly_series(year: int, segmento: Optional[str] = None, uo_level: Optional[str] = None, uo_value: Optional[str] = None) -> tuple[Dict[str, Any], str]:
    """Helper to fetch yearly trend data for visualizations with UO support."""
    # 1. Filtro de segmento
    if segmento and segmento.upper() == "FFVV":
        segment_filter = "AND segmento = 'EMPLEADO FFVV'"
    elif segmento and segmento.upper() in ["ADMINISTRATIVO", "ADMI"]:
        segment_filter = "AND segmento != 'EMPLEADO FFVV' AND segmento != 'PRACTICANTE'"
    else:
        segment_filter = "AND segmento != 'PRACTICANTE'"

    # 2. Filtro de dimensión (UO)
    dim_filter = ""
    if uo_level and uo_value:
        dim_filter = f"AND LOWER({uo_level.lower()}) LIKE '%{uo_value.lower()}%'"

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
            COUNTIF(UPPER(motivo_cese) = 'RENUNCIA') as cesados_voluntarios
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
    months, rotacion_general, rotacion_voluntaria = [], [], []
    headcount, ceses, renuncias = [], [], []
    
    for _, row in df.iterrows():
        mes_num = int(row['mes'])
        # Validar rango de mes
        if 1 <= mes_num <= 12:
            months.append(month_names[mes_num - 1])
            tasa_gen = float(row['tasa_general']) if pd.notna(row['tasa_general']) else 0.0
            tasa_vol = float(row['tasa_voluntaria']) if pd.notna(row['tasa_voluntaria']) else 0.0
            rotacion_general.append(round(tasa_gen * 100, 2))
            rotacion_voluntaria.append(round(tasa_vol * 100, 2))
            headcount.append(int(row['hc_inicial']))
            ceses.append(int(row['total_cesados']))
            renuncias.append(int(row['cesados_voluntarios']))
    
    return {
        "months": months,
        "rotacion_general": rotacion_general,
        "rotacion_voluntaria": rotacion_voluntaria,
        "headcount": headcount,
        "ceses": ceses,
        "renuncias": renuncias
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
    
    Args:
        month: Mes (1-12)
        year: Año
        segment: 'FFVV', 'ADMI' o 'TOTAL'
        uo_level: Nivel organizacional ('uo2', 'uo3', 'uo4')
        uo_value: Nombre de la unidad (ej: 'DIVISION FINANZAS')
    """
    # Extraer parámetros de UO (priorizando explicitos)
    uo_level = uo_level or kwargs.get("uo_level") or kwargs.get("dimension") or "uo2"
    uo_value = uo_value or kwargs.get("uo_value") or kwargs.get("value")

    # 1. Filtro por segmento
    if segmento and segmento.upper() == "FFVV":
        segment_filter = "AND segmento = 'EMPLEADO FFVV'"
    elif segmento and segmento.upper() in ["ADMINISTRATIVO", "ADMI"]:
        segment_filter = "AND segmento != 'EMPLEADO FFVV' AND segmento != 'PRACTICANTE'"
    else:
        segment_filter = "AND segmento != 'PRACTICANTE'"

    # 2. Filtro de dimensión (UO)
    dim_filter = ""
    if uo_level and uo_value:
        dim_filter = f"AND LOWER({uo_level.lower()}) LIKE '%{uo_value.lower()}%'"

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
            COUNTIF(UPPER(motivo_cese) = 'RENUNCIA') as cesados_voluntarios
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
            "color": "red" if rotacion_general > 0.02 else "green"
        },
        {
            "label": "Rotación Voluntaria",
            "value": f"{rotacion_voluntaria:.2%}",
            "delta": f"{row['cesados_voluntarios']} renuncias",
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

    # Filtro de segmento
    if segmento and segmento.upper() == "FFVV":
        segment_filter = "AND segmento = 'EMPLEADO FFVV'"
    elif segmento and segmento.upper() in ["ADMINISTRATIVO", "ADMI"]:
        segment_filter = "AND segmento != 'EMPLEADO FFVV' AND segmento != 'PRACTICANTE'"
    else:
        segment_filter = "AND segmento != 'PRACTICANTE'"

    # Filtro de dimensión (UO)
    dim_filter = ""
    if uo_level and uo_value:
        dim_filter = f"AND LOWER({uo_level.lower()}) LIKE '%{uo_value.lower()}%'"

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
            (SELECT COUNT(DISTINCT CASE WHEN UPPER(motivo_cese) = 'RENUNCIA' THEN nombre_completo END)
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
    kpis = [
        {
            "label": f"Rotación Anual {year}",
            "value": f"{tasa_anual:.2%}",
            "delta": f"{total_cesados} ceses (Avg HC: {avg_hc})",
            "color": "red" if tasa_anual > 0.15 else "green" 
        },
        {
            "label": f"Voluntaria {year}",
            "value": f"{tasa_voluntaria:.2%}",
            "delta": f"{total_renuncias} renuncias",
            "color": "orange" 
        }
    ]
    rb.add_kpi_row(kpis)
    
    context_unit = f"para **{uo_value}**" if uo_value else "a nivel **Corporativo**"
    
    rb.add_text(
        f"En el acumulado del {year}, la unidad **{context_unit}** cerró con una rotación anual del **{tasa_anual:.2%}** ({total_cesados} salidas). "
        f"El headcount promedio se mantuvo en {avg_hc} colaboradores.",
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
    segmento: Optional[str] = None,
    month_start: int = 1,
    month_end: int = 12,
    uo_level: Optional[str] = "uo2",
    uo_value: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Obtiene la tendencia mensual de rotación con soporte de dimensiones.
    
    Args:
        year: Año a analizar
        segmento: Segmento opcional ('FFVV', 'ADMI')
        month_start: Mes inicio
        month_end: Mes fin
        uo_level: Nivel organizacional ('uo2', 'uo3')
        uo_value: Nombre de la unidad
    """
    # Validar consistencia básica
    if month_start < 1: month_start = 1
    if month_end > 12: month_end = 12
    if month_start > month_end: month_start, month_end = 1, 12 # Fallback reset
    
    # Extraer parámetros de UO
    uo_level = uo_level or kwargs.get("uo_level") or kwargs.get("dimension") or "uo2"
    uo_value = uo_value or kwargs.get("uo_value") or kwargs.get("value")

    # Trae el año filtrado por UO
    full_data, series_query = _fetch_yearly_series(year, segmento, uo_level=uo_level, uo_value=uo_value)
    
    if not full_data or not full_data.get("months"):
        return ResponseBuilder().add_text(f"No se encontraron datos para el año {year}").to_dict()

    # --- Lógica de Filtrado (HU-007) ---
    # Los arrays SQL vienen ordenados por mes (1..12).
    # Sin embargo, el resultado de SQL puede no traer meses futuros si no existen.
    # Debemos mapear los meses reales que trajo SQL para filtrar correctamente.
    
    # 1. Reconstruir lista de tuplas para filtrar seguro
    # Estructura temporal: [(mes_nombre, rot_gen, ...), ...]
    zipped_data = []
    
    # Mapper de nombre a numero para filtro preciso
    mes_map = {"Ene":1, "Feb":2, "Mar":3, "Abr":4, "May":5, "Jun":6, 
               "Jul":7, "Ago":8, "Sep":9, "Oct":10, "Nov":11, "Dic":12}
    
    count_items = len(full_data["months"])
    for i in range(count_items):
        m_name = full_data["months"][i]
        m_num = mes_map.get(m_name, 0)
        
        # Solo incluir si está en el rango solicitado
        if month_start <= m_num <= month_end:
             zipped_data.append({
                 "months": m_name,
                 "rotacion_general": full_data["rotacion_general"][i],
                 "rotacion_voluntaria": full_data["rotacion_voluntaria"][i],
                 "headcount": full_data["headcount"][i],
                 "ceses": full_data["ceses"][i],
                 "renuncias": full_data["renuncias"][i]
             })
             
    if not zipped_data:
         context_unit = f"para **{uo_value}**" if uo_value else ""
         return ResponseBuilder().add_text(
             f"No se encontraron datos registrados {context_unit} entre {month_start}/{year} y {month_end}/{year}."
         ).to_dict()

    # 2. Desempaquetar data filtrada
    filtered_series = {
        "months": [x["months"] for x in zipped_data],
        "rotacion_general": [x["rotacion_general"] for x in zipped_data],
        "rotacion_voluntaria": [x["rotacion_voluntaria"] for x in zipped_data],
        "headcount": [x["headcount"] for x in zipped_data],
        "ceses": [x["ceses"] for x in zipped_data],
        "renuncias": [x["renuncias"] for x in zipped_data]
    }

    # 3. Recalcular KPIs sobre el RANGO FILTRADO
    rot_gen_slice = filtered_series["rotacion_general"]
    ceses_slice = filtered_series["ceses"]
    
    avg_rotacion = sum(rot_gen_slice) / len(rot_gen_slice) if rot_gen_slice else 0.0
    max_rotacion = max(rot_gen_slice) if rot_gen_slice else 0.0
    min_rotacion = min(rot_gen_slice) if rot_gen_slice else 0.0
    total_ceses_period = sum(ceses_slice)
    
    rb = ResponseBuilder()
    
    # 4. Construir KPIs
    label_periodo = f"Promedio ({month_start}-{month_end}/{year})" if (month_start > 1 or month_end < 12) else f"Promedio {year}"
    
    kpis = [
        {
            "label": label_periodo,
            "value": f"{avg_rotacion:.2f}%",
            "delta": f"{total_ceses_period} ceses en periodo",
            "color": "blue"
        },
        {
            "label": "Máximo del Periodo",
            "value": f"{max_rotacion:.2f}%",
            "color": "red"
        },
        {
            "label": "Mínimo del Periodo",
            "value": f"{min_rotacion:.2f}%",
            "color": "green"
        }
    ]
    rb.add_kpi_row(kpis)
    
    # 5. Texto de Contexto con Confirmación de Unidad y Segmento
    context_unit = f"para **{uo_value}**" if uo_value else "a nivel **Corporativo**"
    
    seg_names = {"FFVV": "Fuerza de Ventas", "ADMI": "Administrativa", "ADMINISTRATIVO": "Administrativa"}
    context_seg = f" del segmento **{seg_names.get(segmento.upper(), segmento)}**" if segmento else ""
    
    range_text = f"entre los meses {month_start} y {month_end} de {year}" if (month_start > 1 or month_end < 12) else f"para el año {year}"
    
    rb.add_text(
        f"A continuación, se presenta la evolución de rotación {range_text} {context_unit}{context_seg}.",
        variant="standard"
    )
    
    # 6. Data Series Filtrada
    rb.add_data_series(filtered_series, metadata={"year": year, "segmento": segmento or "TOTAL"})
    
    # 7. Debug SQL (Query anual original)
    rb.add_debug_sql(series_query)
    
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
