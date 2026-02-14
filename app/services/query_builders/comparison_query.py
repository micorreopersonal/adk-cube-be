# Implementación de _build_comparison_query

from typing import List, Dict, Any, Optional
from app.core.analytics.registry import METRICS_REGISTRY, DIMENSIONS_REGISTRY
from app.core.config.config import get_settings

settings = get_settings()
CUBE_SOURCE = f"`{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`"


def _build_comparison_query(
    metrics: List[str],
    dimensions: List[str],
    comparison_groups: List[Dict[str, Any]],
    limit: int
) -> str:
    """
    Genera SQL para comparaciones flexibles (periodos, dimensiones, mixtas).
    
    Estrategia:
    1. Crear columna `comparison_group` con CASE WHEN para etiquetar cada grupo
    2. Combinar filtros de todos los grupos con OR en WHERE
    3. GROUP BY dimensions + comparison_group
    4. ORDER BY dimensions + comparison_group
    
    Args:
        metrics: Lista de métricas a calcular
        dimensions: Lista de dimensiones para agrupar (ej: ["mes"])
        comparison_groups: Lista de grupos a comparar
            Ejemplo: [
                {"label": "2024 Q1", "filters": {"anio": 2024, "trimestre": 1}},
                {"label": "2025 Q1", "filters": {"anio": 2025, "trimestre": 1}}
            ]
        limit: Límite de resultados
    
    Returns:
        str: SQL optimizado para comparaciones
    """
    
    # 1. Construir CASE WHEN para comparison_group
    case_when_parts = []
    where_parts = []
    
    for group in comparison_groups:
        label = group["label"]
        filters = group["filters"]
        
        # Construir condición para este grupo
        conditions = []
        for dim, value in filters.items():
            # Obtener definición SQL de la dimensión
            dim_def = DIMENSIONS_REGISTRY.get(dim, {})
            col_sql = dim_def.get("sql", dim)
            
            if isinstance(value, list):
                # Lista de valores → IN clause
                formatted_values = []
                for v in value:
                    if isinstance(v, str):
                        formatted_values.append(f"'{v}'")
                    else:
                        formatted_values.append(str(v))
                conditions.append(f"{col_sql} IN ({', '.join(formatted_values)})")
            else:
                # Valor único → =
                if isinstance(value, str):
                    conditions.append(f"{col_sql} = '{value}'")
                else:
                    conditions.append(f"{col_sql} = {value}")
        
        condition_str = " AND ".join(conditions)
        
        # Agregar a CASE WHEN
        case_when_parts.append(f"        WHEN {condition_str} THEN '{label}'")
        
        # Agregar a WHERE (con OR)
        where_parts.append(f"({condition_str})")
    
    # Construir CASE WHEN SQL
    case_when_sql = f"""CASE
{chr(10).join(case_when_parts)}
    END AS comparison_group"""
    
    where_sql = " OR ".join(where_parts)
    
    # 2. Construir SELECT items
    select_items = [case_when_sql]
    
    # Agregar dimensiones
    for dim in dimensions:
        dim_def = DIMENSIONS_REGISTRY.get(dim, {})
        col_sql = dim_def.get("sql", dim)
        select_items.append(f"{col_sql} AS {dim}")
    
    # Agregar métricas
    for metric in metrics:
        metric_def = METRICS_REGISTRY.get(metric, {})
        metric_sql = metric_def.get("sql", metric)
        
        # Si la métrica tiene una fórmula SQL compleja, usarla
        if metric_sql and metric_sql != metric:
            select_items.append(f"{metric_sql} AS {metric}")
        else:
            # Métrica simple, asumir que es una columna directa
            select_items.append(f"{metric} AS {metric}")
    
    # 3. Construir GROUP BY
    group_by_cols = ["comparison_group"]
    for dim in dimensions:
        dim_def = DIMENSIONS_REGISTRY.get(dim, {})
        col_sql = dim_def.get("sql", dim)
        group_by_cols.append(col_sql)
    
    # 4. Construir ORDER BY
    order_by_cols = []
    for dim in dimensions:
        dim_def = DIMENSIONS_REGISTRY.get(dim, {})
        # Verificar si la dimensión tiene sorting especial
        if dim_def.get("sorting") == "numeric":
            order_by_cols.append(f"{dim} ASC")
        else:
            order_by_cols.append(f"{dim} ASC")
    order_by_cols.append("comparison_group ASC")
    
    # 5. Ensamblar SQL
    sql = f"""
SELECT 
    {',
    '.join(select_items)}
FROM {CUBE_SOURCE}
WHERE segmento != 'PRACTICANTE' AND ({where_sql})
GROUP BY {', '.join(group_by_cols)}
ORDER BY {', '.join(order_by_cols)}
LIMIT {limit}
"""
    
    return sql.strip()
