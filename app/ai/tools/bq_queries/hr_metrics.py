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

def _fetch_yearly_series(year: int, segment: Optional[str] = None) -> tuple[Dict[str, Any], str]:
    """Helper to fetch yearly trend data for visualizations."""
    # Filtro de segmento
    if segment and segment.upper() == "FFVV":
        segment_filter = "AND segmento = 'EMPLEADO FFVV'"
    elif segment and segment.upper() in ["ADMINISTRATIVO", "ADMI"]:
        segment_filter = "AND segmento != 'EMPLEADO FFVV' AND segmento != 'PRACTICANTE'"
    else:
        segment_filter = "AND segmento != 'PRACTICANTE'"

    query = f"""
    WITH 
    MonthlyHC AS (
        SELECT 
            EXTRACT(MONTH FROM DATE_ADD(fecha_corte, INTERVAL 1 MONTH)) as mes,
            COUNT(DISTINCT codigo_persona) as hc_inicial
        FROM `{table_id}`
        WHERE EXTRACT(YEAR FROM fecha_corte) = {year}
        AND estado = 'Activo'
        {segment_filter}
        GROUP BY 1
    ),
    MonthlyCeses AS (
        SELECT 
            EXTRACT(MONTH FROM fecha_cese) as mes,
            COUNT(*) as total_cesados,
            COUNTIF(UPPER(motivo_cese) = 'RENUNCIA') as cesados_voluntarios
        FROM `{table_id}`
        WHERE EXTRACT(YEAR FROM fecha_cese) = {year}
        {segment_filter}
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


def get_monthly_attrition(month: int, year: int, segment: Optional[str] = None) -> Dict[str, Any]:
    """
    Calcula la tasa de rotación mensual según las reglas de negocio:
    - Excluye PRACTICANTE.
    - Criterio Voluntario: motivo_cese = 'RENUNCIA' (exacto).
    - Fórmula: (Suma de Cesados del Mes / Headcount Inicial del Mes).
    - HC Inicial = Personal Activo del mes anterior.
    """
    # Filtro por segmento
    if segment and segment.upper() == "FFVV":
        segment_filter = "AND segmento = 'EMPLEADO FFVV'"
    elif segment and segment.upper() in ["ADMINISTRATIVO", "ADMI"]:
        segment_filter = "AND segmento != 'EMPLEADO FFVV' AND segmento != 'PRACTICANTE'"
    else:
        segment_filter = "AND segmento != 'PRACTICANTE'"

    query = f"""
    WITH 
    -- Obtener HC del mes anterior (Estrictamente t-1)
    HcInicial AS (
        SELECT COUNT(DISTINCT codigo_persona) as hc 
        FROM `{table_id}`
        WHERE EXTRACT(YEAR FROM fecha_corte) = {year if month > 1 else year - 1}
        AND EXTRACT(MONTH FROM fecha_corte) = {month - 1 if month > 1 else 12}
        AND estado = 'Activo'
        {segment_filter}
    ),
    -- Obtener Cesados del mes
    Cesados AS (
        SELECT 
            COUNT(*) as total_cesados,
            COUNTIF(UPPER(motivo_cese) = 'RENUNCIA') as cesados_voluntarios
        FROM `{table_id}`
        WHERE EXTRACT(MONTH FROM fecha_cese) = {month}
        AND EXTRACT(YEAR FROM fecha_cese) = {year}
        {segment_filter}
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

    # --- Lógica de Etiquetado Dinámico (Naming Strategy) ---
    # Diccionario escalable para "humanizar" los códigos de segmento
    segment_names = {
        "FFVV": "Fuerza de Ventas",
        "ADMINISTRATIVO": "Administrativa",
        "ADMI": "Administrativa"
    }
    
    # Determinar sufijo para títulos y textos
    if segment:
        clean_seg = segment.upper()
        # Si está en el mapa, usar nombre bonito, sino usar el código limpio
        seg_display = segment_names.get(clean_seg, clean_seg) 
        kpi_title = f"Rotación {seg_display}"
        text_context = f"la rotación de {seg_display}"
    else:
        kpi_title = "Rotación General"
        text_context = "la rotación general"
    
    # 1. KPIs Principales
    kpis = [
        {
            "label": kpi_title,
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
            "value": str(int(row['hc_inicial'])),
            "color": "blue"
        }
    ]
    rb.add_kpi_row(kpis)

    # 2. Insight Automático
    if rotacion_general > 0.0:
        rb.add_text(
            f"En {month}/{year}, {text_context} fue del {rotacion_general:.2%}, "
            f"con {int(row['total_cesados'])} salidas totales sobre una base de {int(row['hc_inicial'])} colaboradores.",
            variant="insight", severity="info"
        )

    # 3. Debug SQL
    rb.add_debug_sql(query)

    return rb.to_dict()

def get_talent_alerts(month: int, year: int) -> Dict[str, Any]:
    """
    Detecta fugas de talento clave (Hiper/Hipo) en el mes especificado.
    """
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

def get_yearly_attrition(year: int, segment: Optional[str] = None) -> Dict[str, Any]:
    """
    Calcula la rotación anual según fórmula oficial:
    Rotación Anual = Total Cesados Únicos del Año / Promedio Headcount Anualizado
    """
    # Filtro de segmento
    if segment and segment.upper() == "FFVV":
        segment_filter = "AND segmento = 'EMPLEADO FFVV'"
    elif segment and segment.upper() in ["ADMINISTRATIVO", "ADMI"]:
        segment_filter = "AND segmento != 'EMPLEADO FFVV' AND segmento != 'PRACTICANTE'"
    else:
        segment_filter = "AND segmento != 'PRACTICANTE'"

    query = f"""
    WITH 
    MonthlyHC AS (
        SELECT 
            EXTRACT(MONTH FROM fecha_corte) as mes,
            COUNT(DISTINCT codigo_persona) as hc
        FROM `{table_id}`
        WHERE EXTRACT(YEAR FROM fecha_corte) = {year}
        AND estado = 'Activo'
        {segment_filter}
        GROUP BY 1
    ),
    AnnualStats AS (
        SELECT 
            AVG(hc) as avg_hc,
            (SELECT COUNT(DISTINCT nombre_completo) 
             FROM `{table_id}` 
             WHERE EXTRACT(YEAR FROM fecha_cese) = {year}
             {segment_filter}
            ) as total_cesados,
            (SELECT COUNT(DISTINCT CASE WHEN UPPER(motivo_cese) = 'RENUNCIA' THEN nombre_completo END)
             FROM `{table_id}` 
             WHERE EXTRACT(YEAR FROM fecha_cese) = {year}
             {segment_filter}
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

    # 1. KPIs Anuales
    kpis = [
        {
            "label": f"Rotación Anual {year}",
            "value": f"{tasa_anual:.2%}",
            "delta": f"{total_cesados} ceses",
            "color": "red" if tasa_anual > 0.15 else "green" # Umbral anual aprox 15%
        },
        {
            "label": f"Voluntaria {year}",
            "value": f"{tasa_voluntaria:.2%}",
            "delta": f"{total_renuncias} renuncias",
            "color": "orange" 
        },
        {
            "label": "HC Promedio",
            "value": str(avg_hc),
            "color": "blue"
        }
    ]
    rb.add_kpi_row(kpis)
    
    rb.add_text(
        f"En el acumulado del {year}, la compañía cerró con una rotación anual del **{tasa_anual:.2%}** ({total_cesados} salidas). "
        f"El headcount promedio se mantuvo en {avg_hc} colaboradores.",
        variant="insight"
    )

    # 2. Contexto Anual (Data Series)
    series_data, series_query = _fetch_yearly_series(year, segment)
    if series_data:
        rb.add_data_series(series_data, metadata={"year": year, "segment": segment or "TOTAL"})

    # 3. Debug SQL (Incluye ambas queries)
    rb.add_debug_sql(f"-- Query Anual KPI:\n{query}\n\n-- Query Tendencia Mensual:\n{series_query}")

    return rb.to_dict()

def get_monthly_trend(year: int, segment: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene la tendencia mensual de rotación para todo un año.
    Retorna datos estructurados para visualización interactiva (gráficos + tabla).
    
    Args:
        year: Año a analizar
        segment: Segmento opcional ('FFVV', 'ADMINISTRATIVO', 'TOTAL')
    
    Returns:
        VisualDataPackage con data_series para visualización interactiva
    """
    series_data, series_query = _fetch_yearly_series(year, segment)
    
    if not series_data:
        return ResponseBuilder().add_text(f"No se encontraron datos para el año {year}").to_dict()

    # Calcular KPIs resumen desde los datos ya procesados
    rotacion_general = series_data["rotacion_general"]
    ceses = series_data["ceses"]
    
    avg_rotacion = sum(rotacion_general) / len(rotacion_general) if rotacion_general else 0.0
    max_rotacion = max(rotacion_general) if rotacion_general else 0.0
    min_rotacion = min(rotacion_general) if rotacion_general else 0.0
    total_ceses_year = sum(ceses)
    
    rb = ResponseBuilder()
    
    # 1. KPIs Resumen
    kpis = [
        {
            "label": f"Promedio {year}",
            "value": f"{avg_rotacion:.2f}%",
            "delta": f"{total_ceses_year} ceses totales",
            "color": "blue"
        },
        {
            "label": "Máximo Mensual",
            "value": f"{max_rotacion:.2f}%",
            "color": "red"
        },
        {
            "label": "Mínimo Mensual",
            "value": f"{min_rotacion:.2f}%",
            "color": "green"
        }
    ]
    rb.add_kpi_row(kpis)
    
    # 2. Texto introductorio
    rb.add_text(
        f"A continuación, se presenta la evolución mensual de la rotación para el año {year}. "
        f"Puedes alternar entre gráfico de línea, barras o tabla detallada.",
        variant="standard"
    )
    
    # 3. Data Series para visualización interactiva
    rb.add_data_series(series_data, metadata={"year": year, "segment": segment or "TOTAL"})
    
    # 4. Debug SQL
    rb.add_debug_sql(series_query)
    
    return rb.to_dict()
