import json
from datetime import datetime
from typing import Optional
from app.services.bigquery import get_bq_service
from app.core.config import get_settings

settings = get_settings()
bq_service = get_bq_service()

def get_monthly_attrition(month: int, year: int, segment: Optional[str] = None):
    """
    Calcula la tasa de rotación mensual según las reglas de negocio:
    - Excluye PRACTICANTE.
    - Criterio Voluntario: motivo_cese contiene 'RENUNCIA'.
    - Fórmula: (Suma de Cesados del Mes / Headcount Inicial del Mes).
    """
    table_id = f"{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}"
    
    # Filtro por segmento core
    segment_filter = ""
    if segment == "FFVV":
        segment_filter = "AND segmento = 'EMPLEADO FFVV'"
    elif segment == "ADMI":
        segment_filter = "AND segmento != 'EMPLEADO FFVV' AND segmento != 'PRACTICANTE'"
    else:
        segment_filter = "AND segmento != 'PRACTICANTE'"

    query = f"""
    WITH 
    -- 1. Intentar obtener HC del mes anterior (Ideal)
    HcAnterior AS (
        SELECT COUNT(*) as hc 
        FROM `{table_id}`
        WHERE fecha_corte = DATE_SUB(DATE('{year}-{month}-01'), INTERVAL 1 MONTH)
        {segment_filter}
    ),
    -- 2. Intentar obtener HC del mes actual (Fallback)
    HcActual AS (
        SELECT COUNT(*) as hc
        FROM `{table_id}`
        WHERE EXTRACT(MONTH FROM fecha_corte) = {month}
        AND EXTRACT(YEAR FROM fecha_corte) = {year}
        {segment_filter}
    ),
    -- 3. Obtener Cesados del mes
    Cesados AS (
        SELECT 
            COUNT(*) as total_cesados,
            COUNTIF(LOWER(motivo_cese) LIKE '%renuncia%') as cesados_voluntarios
        FROM `{table_id}`
        WHERE EXTRACT(MONTH FROM fecha_cese) = {month}
        AND EXTRACT(YEAR FROM fecha_cese) = {year}
        {segment_filter}
    )
    SELECT 
        -- Lógica de Fallback: Si no hay anterior, usar actual.
        COALESCE(h_ant.hc, h_act.hc, 0) as hc_inicial,
        COALESCE(c.total_cesados, 0) as total_cesados,
        COALESCE(c.cesados_voluntarios, 0) as cesados_voluntarios,
        
        SAFE_DIVIDE(COALESCE(c.total_cesados, 0), NULLIF(COALESCE(h_ant.hc, h_act.hc, 0), 0)) as tasa_rotacion_general,
        SAFE_DIVIDE(COALESCE(c.cesados_voluntarios, 0), NULLIF(COALESCE(h_ant.hc, h_act.hc, 0), 0)) as tasa_rotacion_voluntaria
    FROM Cesados c
    CROSS JOIN HcAnterior h_ant
    CROSS JOIN HcActual h_act
    """
    
    result = bq_service.execute_query(query)
    
    # Convertir DataFrame a formato serializable para ADK usando json estándar
    if hasattr(result, 'to_json'):
        return json.loads(result.to_json(orient='records', date_format='iso'))
    return result

def get_talent_alerts(month: int, year: int):
    """
    Identifica ceses de Hipers (7) e Hipos (8, 9) en el mes.
    """
    table_id = f"{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}"
    
    query = f"""
    SELECT 
        nombre, 
        posicion, 
        motivo_cese,
        mapeo_talento_ultimo_anio as talento_score,
        CASE 
            WHEN mapeo_talento_ultimo_anio = 7 THEN 'Hiper'
            WHEN mapeo_talento_ultimo_anio IN (8, 9) THEN 'Hipo'
        END as categoria_talento
    FROM `{table_id}`
    WHERE EXTRACT(MONTH FROM fecha_cese) = {month}
    AND EXTRACT(YEAR FROM fecha_cese) = {year}
    AND mapeo_talento_ultimo_anio IN (7, 8, 9)
    ORDER BY mapeo_talento_ultimo_anio DESC
    """
    
    result = bq_service.execute_query(query)
    
    # Convertir DataFrame a formato serializable para ADK usando json estándar
    if hasattr(result, 'to_json'):
        return json.loads(result.to_json(orient='records', date_format='iso'))
    return result
