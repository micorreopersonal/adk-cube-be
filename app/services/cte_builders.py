"""
CTE Builders para Métricas Complejas

Este módulo contiene las definiciones de Common Table Expressions (CTEs)
necesarias para calcular métricas que requieren Window Functions.
"""

from typing import List, Dict, Any, Optional
from app.core.analytics.registry import DIMENSIONS_REGISTRY
from app.core.config.config import get_settings

settings = get_settings()
CUBE_SOURCE = f"`{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`"


def build_headcount_base_cte(
    dimensions: List[str],
    filters: Optional[Dict[str, Any]] = None,
    adhoc_groups: List[Any] = None  # NUEVO
) -> str:
    """
    Genera el CTE 'headcount_base' que calcula métricas de Headcount y Rotación
    usando Window Functions (LAG, AVG OVER, SUM OVER).
    
    Este CTE es la base para todas las métricas complejas de headcount y rotación.
    
    Args:
        dimensions: Lista de dimensiones para agrupar (además de periodo/anio/mes)
        filters: Filtros aplicados
        adhoc_groups: Grupos dinámicos
    
    Returns:
        str: SQL del CTE completo
    """
    
    # Pre-procesar grupos ad-hoc
    adhoc_map = {}
    if adhoc_groups:
        for grp in adhoc_groups:
            dim = getattr(grp, "dimension", None) or grp.get("dimension")
            if dim:
                adhoc_map[dim] = grp

    # 1. Construir dimensiones dinámicas para GROUP BY y PARTITION BY
    dim_select = ""
    dim_group = ""
    dim_partition = ""
    dim_partition_clean = "1"
    
    # Determinar si hay dimensión de agrupación (además de temporales)
    group_dims = [d for d in dimensions if d not in ["periodo", "anio", "mes", "month", "year"]]
    
    if group_dims:
        # Usar la primera dimensión no-temporal como partition key
        group_by_dim = group_dims[0]
        
        if group_by_dim in DIMENSIONS_REGISTRY:
            dim_def = DIMENSIONS_REGISTRY[group_by_dim]
            base_col_sql = dim_def.get("sql", group_by_dim) if isinstance(dim_def, dict) else group_by_dim
            
            # --- AD-HOC LOGIC ---
            if group_by_dim in adhoc_map:
                grp = adhoc_map[group_by_dim]
                label = getattr(grp, "label", None) or grp.get("label")
                values = getattr(grp, "values", None) or grp.get("values")
                vals_str = ", ".join([f"'{v}'" for v in values])
                col_sql = f"CASE WHEN {base_col_sql} IN ({vals_str}) THEN '{label}' ELSE {base_col_sql} END"
            else:
                col_sql = base_col_sql
            # --------------------

            dim_select = f"{col_sql} AS {group_by_dim},"
            dim_group = f", {group_by_dim}"
            dim_partition = f", {col_sql}"
            # CRITICAL: Usar el ALIAS en CTEs internos, no el SQL raw
            dim_partition_clean = group_by_dim
        else:
            dim_partition_clean = "1"
    else:
        dim_partition_clean = "1"

    
    # 2. Construir filtros WHERE
    where_clauses = ["segmento != 'PRACTICANTE'"]
    
    # Detectar año(s) para ampliar rango (necesitamos Diciembre del año anterior para LAG)
    years = []
    if filters:
        for dim_key, value in filters.items():
            if dim_key in ["anio", "year"]:
                if isinstance(value, list):
                    years = [int(v) for v in value]
                else:
                    years = [int(value)]
                break

    # Rango ampliado de fechas — use min/max to cover all requested years
    if years:
        min_year = min(years)
        max_year = max(years)
        where_clauses.append(f"periodo BETWEEN DATE('{min_year-1}-12-01') AND DATE('{max_year}-12-31')")
    
    # Agregar filtros adicionales (excepto temporales que se aplicarán al final)
    if filters:
        for dim_key, value in filters.items():
            if dim_key in ["periodo", "anio", "mes", "month", "year"]:
                continue  # Filtros temporales se aplican después de LAG
            
            dim_def = DIMENSIONS_REGISTRY.get(dim_key)
            if not dim_def:
                continue
            
            col_sql = dim_def["sql"] if isinstance(dim_def, dict) else dim_def
            
            # Determinar si es numérico
            is_numeric = False
            if isinstance(dim_def, dict):
                if dim_def.get("sorting") == "numeric" or dim_def.get("type") in ["integer", "float", "number", "numeric"]:
                    is_numeric = True
            
            def format_val(v):
                if isinstance(v, (int, float)):
                    return str(v)
                if isinstance(v, str) and is_numeric and v.replace(".", "", 1).isdigit():
                    return v
                return f"'{v}'"
            
            if isinstance(value, list):
                vals = ", ".join([format_val(v) for v in value])
                where_clauses.append(f"{col_sql} IN ({vals})")
            else:
                where_clauses.append(f"{col_sql} = {format_val(value)}")
    
    where_block = " AND ".join(where_clauses)
    
    # 3. Generar SQL del CTE
    cte_sql = f"""
    headcount_base AS (
        -- Paso 1: Snapshots Mensuales (Agregación Base)
        WITH MonthlySnapshots AS (
            SELECT
                periodo,
                EXTRACT(YEAR FROM periodo) as anio,
                EXTRACT(MONTH FROM periodo) as mes,
                {dim_select}
                COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END) AS hc_final,
                COUNT(DISTINCT CASE WHEN estado = 'Cesado' THEN codigo_persona END) AS ceses,
                COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) LIKE '%renuncia%' THEN codigo_persona END) AS ceses_voluntarios,
                COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) NOT LIKE '%renuncia%' THEN codigo_persona END) AS ceses_involuntarios
            FROM {CUBE_SOURCE}
            WHERE {where_block}
            GROUP BY periodo, anio, mes{dim_group}
        ),
        
        -- Paso 2: Calcular HC Inicial (LAG)
        MetricsCalculation AS (
            SELECT
                *,
                LAG(hc_final) OVER (PARTITION BY {dim_partition_clean} ORDER BY periodo) AS hc_inicial_raw
            FROM MonthlySnapshots
        ),
        
        -- Paso 3: Ajustar HC Inicial (Fallback para NULL)
        AdjustedMetrics AS (
            SELECT
                *,
                CASE 
                    WHEN hc_inicial_raw IS NULL THEN hc_final
                    ELSE hc_inicial_raw 
                END AS hc_inicial
            FROM MetricsCalculation
        ),
        
        -- Paso 4: Calcular Métricas Finales (Promedios, Acumulados, Tasas)
        FinalMetrics AS (
            SELECT
                *,
                -- HC Promedio Mensual (para compatibilidad con reportes legacy)
                SAFE_DIVIDE(hc_inicial + hc_final, 2) AS headcount_promedio_mensual,
                
                -- HC Promedio Acumulado (YTD) - PROMEDIO SIMPLE de HC Finales
                -- Fórmula de Negocio: (HC_ene + HC_feb + ... + HC_mes) / n_meses
                AVG(hc_final) OVER (
                    PARTITION BY anio, {dim_partition_clean} 
                    ORDER BY mes 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as hc_promedio_acumulado,
                
                -- Ceses Acumulados (YTD)
                SUM(ceses) OVER (
                    PARTITION BY anio, {dim_partition_clean} 
                    ORDER BY mes 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as ceses_acumulado,
                SUM(ceses_voluntarios) OVER (
                    PARTITION BY anio, {dim_partition_clean} 
                    ORDER BY mes 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as ceses_voluntarios_acumulado,
                SUM(ceses_involuntarios) OVER (
                    PARTITION BY anio, {dim_partition_clean} 
                    ORDER BY mes 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as ceses_involuntarios_acumulado
            FROM AdjustedMetrics
        )
        
        -- Paso 5: Calcular Tasas de Rotación (FUENTE DE VERDAD)
        SELECT
            *,
            -- Tasas Mensuales: Ceses del mes / HC Final del mes anterior
            -- hc_inicial = HC Final del mes anterior (LAG)
            SAFE_DIVIDE(ceses, hc_inicial) * 100 AS tasa_rotacion_mensual,
            SAFE_DIVIDE(ceses_voluntarios, hc_inicial) * 100 AS tasa_rotacion_mensual_voluntaria,
            SAFE_DIVIDE(ceses_involuntarios, hc_inicial) * 100 AS tasa_rotacion_mensual_involuntaria,
            
            -- Tasas Anuales (YTD): Ceses acumulados / HC Promedio YTD
            -- hc_promedio_acumulado = Promedio simple de HC Finales
            SAFE_DIVIDE(ceses_acumulado, hc_promedio_acumulado) * 100 AS tasa_rotacion_anual,
            SAFE_DIVIDE(ceses_voluntarios_acumulado, hc_promedio_acumulado) * 100 AS tasa_rotacion_anual_voluntaria,
            SAFE_DIVIDE(ceses_involuntarios_acumulado, hc_promedio_acumulado) * 100 AS tasa_rotacion_anual_involuntaria
        FROM FinalMetrics
    )
    """
    
    return cte_sql


# Registro de CTEs disponibles
CTE_BUILDERS = {
    "headcount_base": build_headcount_base_cte
}
