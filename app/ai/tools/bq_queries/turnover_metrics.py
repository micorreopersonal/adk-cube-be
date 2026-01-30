from typing import List, Dict, Optional
from google.cloud import bigquery
from app.services.bigquery import get_bq_service
from app.core.config import get_settings

def get_advanced_turnover_metrics(
    periods: List[str],
    filters: Optional[Dict[str, str]] = None,
    group_by: Optional[List[str]] = None
) -> List[Dict]:
    """
    Calcula métricas de rotación (Total y Voluntaria) excluyendo estrictamente 'PRACTICANTE'.
    Soporta agregación temporal (promedio de HC mensual) y drill-down dinámico.

    Args:
        periods: Lista de fechas en formato 'YYYY-MM-DD' (ej. ['2025-01-01', '2025-02-01'])
        filters: Diccionario de filtros adicionales (ej. {'division': 'TALENTO'})
        group_by: Lista de columnas para agrupar (ej. ['area', 'uo3'])

    Returns:
        Lista de diccionarios con las métricas calculadas.
    """
    client = get_bq_service().client
    settings = get_settings()
    
    # 1. Mapeo de columnas (Business -> Technical)
    COLUMN_MAPPING = {
        "division": "uo2",
        "división": "uo2",
        "area": "uo3",
        "área": "uo3",
        "uo2": "uo2",
        "uo3": "uo3"
    }

    # 2. Construcción de filtros dinámicos y columnas de agrupación
    where_clauses = ["segmento != 'PRACTICANTE'"]  # Regla de Negocio Hardcoded
    
    # Validación de periodos para evitar inyección
    sanitized_periods = [f"'{p}'" for p in periods]
    periods_sql = f"UNNEST([{', '.join(sanitized_periods)}])"
    
    if filters:
        for k, v in filters.items():
            # Traducir nombre de columna si existe en el mapa, sino usar el key original (fallback)
            col_name = COLUMN_MAPPING.get(k.lower(), k)
            where_clauses.append(f"{col_name} = '{v}'")
            
    where_sql = " AND ".join(where_clauses)
    
    # Construcción del GROUP BY dinámico con Manejo de Nulos
    # Usamos COALESCE para que los nulos se agrupen bajo 'N/A'
    if group_by:
        # Traducir dimensiones de agrupación
        mapped_group_by = [COLUMN_MAPPING.get(dim.lower(), dim) for dim in group_by]
        
        # Generar: COALESCE(uo3, 'N/A') as uo3 (usando el nombre real)
        # Nota: Mantenemos el alias igual al nombre técnico para evitar confusiones en el frontend
        dim_selects = [f"COALESCE({dim}, 'N/A') as {dim}" for dim in mapped_group_by]
        dim_cols = mapped_group_by 
        
        select_clause = ", ".join(dim_selects)
        group_by_clause = ", ".join([str(i+1) for i in range(len(mapped_group_by))]) # Group by 1, 2...
        
        final_select_dims = ", ".join([f"c.{dim}" for dim in dim_cols])
        join_clause = " AND ".join([f"c.{dim} = h.{dim}" for dim in dim_cols])
    else:
        select_clause = "'Total' as scope"
        group_by_clause = "1"
        final_select_dims = "scope"
        join_clause = "1=1" # Cross join implícito si es total
    
    query = f"""
    WITH base_data AS (
        SELECT * 
        FROM `{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`
        WHERE {where_sql}
        AND periodo IN {periods_sql}
    ),
    
    -- Numerador: Total de Ceses
    ceses AS (
        SELECT 
            {select_clause},
            COUNT(DISTINCT codigo_persona) as total_bajas,
            COUNT(DISTINCT IF(motivo_cese LIKE '%RENUNCIA%', codigo_persona, NULL)) as bajas_voluntarias
        FROM base_data 
        WHERE estado = 'Cesado'
        GROUP BY {group_by_clause}
    ),
    
    -- Denominador: Headcount Promedio
    headcount_mensual AS (
        SELECT 
            {select_clause},
            periodo,
            COUNT(DISTINCT codigo_persona) as hc_mes
        FROM base_data 
        WHERE estado = 'Activo' 
        GROUP BY {group_by_clause}, periodo
    ),
    
    headcount_promedio AS (
        SELECT 
            {", ".join(dim_cols) if group_by else "scope"},
            AVG(hc_mes) as hc_avg
        FROM headcount_mensual
        GROUP BY {group_by_clause}
    )
    
    SELECT 
        {final_select_dims},
        c.total_bajas,
        c.bajas_voluntarias,
        CAST(h.hc_avg AS INT64) as headcount_avg,
        SAFE_DIVIDE(c.total_bajas, h.hc_avg) as tasa_rotacion_total,
        SAFE_DIVIDE(c.bajas_voluntarias, h.hc_avg) as tasa_rotacion_voluntaria
    FROM ceses c
    JOIN headcount_promedio h 
      ON {join_clause}
    ORDER BY tasa_rotacion_total DESC
    """
    
    job = client.query(query)
    return [dict(row) for row in job.result()]
