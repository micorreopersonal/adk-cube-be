"""
Comparison Builder for CTE-based Metrics

This module adds comparison query support to the YTD optimized query builder.
When comparing groups using calculated metrics (like tasa_rotacion_mensual),
we need to use the CTE instead of querying the raw table directly.
"""

from typing import List, Dict, Any
from app.services.cte_builders import build_headcount_base_cte
from app.core.analytics.registry import METRICS_REGISTRY, DIMENSIONS_REGISTRY
from app.core.config.config import get_settings

settings = get_settings()


def build_ytd_comparison_with_cte(
    metrics: List[str],
    dimensions: List[str],
    comparison_groups: List[Dict[str, Any]],
    limit: int = 5000
) -> str:
    """
    Genera query de comparación usando el CTE para métricas calculadas.
    
    Estrategia:
    1. Generar el CTE con todas las dimensiones de comparación
    2. Crear CASE WHEN para etiquetar grupos
    3. SELECT desde el CTE (no desde tabla raw)
    
    Args:
        metrics: Lista de métricas a comparar
        dimensions: Dimensiones temporales (ej: ["mes"])
        comparison_groups: Grupos a comparar
        limit: Límite de resultados
    
    Returns:
        str: SQL con CTE + comparación
    """
    
    # 1. Recopilar todos los filtros de todos los grupos
    all_filters = {}
    comparison_dimensions = set()
    
    for group in comparison_groups:
        for dim, value in group["filters"].items():
            # Agregar dimensión a la lista
            comparison_dimensions.add(dim)
            
            # Agregar valores al filtro combinado
            if dim not in all_filters:
                all_filters[dim] = []
            
            if isinstance(value, list):
                all_filters[dim].extend(value)
            else:
                all_filters[dim].append(value)
    
    # Deduplicate filter values
    for dim in all_filters:
        all_filters[dim] = list(set(all_filters[dim]))
    
    # 2. Construir CTE con todas las dimensiones de comparación
    cte_dimensions = list(dimensions) + list(comparison_dimensions)
    cte_sql = build_headcount_base_cte(cte_dimensions, all_filters)
    
    # 3. Construir CASE WHEN para comparison_group
    case_when_parts = []
    
    for group in comparison_groups:
        label = group["label"]
        filters = group["filters"]
        
        conditions = []
        for dim, value in filters.items():
            # CRITICAL: Usar el alias (dim), no el SQL raw para el CASE WHEN
            # porque ya fue calculado en el CTE
            col_sql = dim
            
            if isinstance(value, list):
                formatted_values = []
                for v in value:
                    if isinstance(v, str):
                        formatted_values.append(f"'{v}'")
                    else:
                        formatted_values.append(str(v))
                conditions.append(f"{col_sql} IN ({', '.join(formatted_values)})")
            else:
                if isinstance(value, str):
                    conditions.append(f"{col_sql} = '{value}'")
                else:
                    conditions.append(f"{col_sql} = {value}")
        
        condition_str = " AND ".join(conditions)
        case_when_parts.append(f"        WHEN {condition_str} THEN '{label}'")
    
    case_when_sql = f"""CASE
{chr(10).join(case_when_parts)}
    END AS comparison_group"""
    
    # 4. Construir SELECT items
    select_items = [case_when_sql]
    
    # Agregar dimensiones temporales
    for dim in dimensions:
        select_items.append(dim)
    
    # Agregar métricas
    for metric in metrics:
        metric_def = METRICS_REGISTRY.get(metric, {})
        metric_sql = metric_def.get("sql", metric)
        if metric_sql != metric:
            select_items.append(f"{metric_sql} AS {metric}")
        else:
            select_items.append(metric)
    
    # 5. Construir ORDER BY
    order_by_cols = []
    for dim in dimensions:
        order_by_cols.append(f"{dim} ASC")
    order_by_cols.append("comparison_group ASC")
    
    # 6. Ensamblar SQL final
    select_clause = ',\\n    '.join(select_items)
    
    sql = f"""
WITH {cte_sql}

SELECT 
    {select_clause}
FROM headcount_base
ORDER BY {', '.join(order_by_cols)}
LIMIT {limit}
"""
    
    return sql.strip()
