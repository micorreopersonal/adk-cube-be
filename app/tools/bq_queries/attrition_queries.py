from app.core.config import get_settings

settings = get_settings()

def get_monthly_attrition_query(year: int, month: int, uo_level: str = None, uo_value: str = None):
    """
    Genera la consulta para calcular la rotación mensual.
    Fórmula: (Suma de Cesados del Mes / Headcount Inicial del Mes)
    Excluye: PRACTICANTE
    """
    where_clause = f"EXTRACT(YEAR FROM fecha_corte) = {year} AND EXTRACT(MONTH FROM fecha_corte) = {month}"
    if uo_level and uo_value:
        where_clause += f" AND {uo_level} = '{uo_value}'"

    query = f"""
    WITH current_month_stats AS (
        # Cesados del mes
        SELECT 
            COUNTIF(is_cesado = 1) as total_cesados,
            COUNTIF(is_cesado = 1 AND LOWER(motivo_cese) LIKE '%renuncia%') as cesados_voluntarios,
            COUNTIF(segmento = 'EMPLEADO FFVV') as headcount_ffvv,
            COUNTIF(segmento != 'EMPLEADO FFVV' AND segmento != 'PRACTICANTE') as headcount_admi
        FROM `{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`
        WHERE {where_clause}
        AND segmento != 'PRACTICANTE'
    ),
    previous_month_headcount AS (
        # Headcount inicial (cierre del mes anterior)
        SELECT COUNT(*) as headcount_inicial
        FROM `{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`
        WHERE EXTRACT(DATE FROM fecha_corte) = DATE_SUB(DATE('{year}-{month}-01'), INTERVAL 1 DAY)
        AND segmento != 'PRACTICANTE'
        {f"AND {uo_level} = '{uo_value}'" if uo_level and uo_value else ""}
    )
    SELECT 
        c.*,
        p.headcount_inicial,
        SAFE_DIVIDE(c.total_cesados, p.headcount_inicial) as ratio_rotacion_general,
        SAFE_DIVIDE(c.cesados_voluntarios, p.headcount_inicial) as ratio_rotacion_voluntaria
    FROM current_month_stats c, previous_month_headcount p
    """
    return query

def get_talent_attrition_query():
    """
    Consulta para identificar ceses de Talento Clave (Hipers e Hipos).
    """
    return f"""
    SELECT 
        nombre_completo, 
        posicion, 
        motivo_cese,
        CASE 
            WHEN mapeo_talento_ultimo_anio = 7 THEN 'Hiper'
            WHEN mapeo_talento_ultimo_anio IN (8, 9) THEN 'Hipo'
        END as categoria_talento
    FROM `{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`
    WHERE is_cesado = 1 
    AND mapeo_talento_ultimo_anio IN (7, 8, 9)
    AND segmento != 'PRACTICANTE'
    """
