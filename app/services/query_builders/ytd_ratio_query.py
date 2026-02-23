"""
YTD Ratio Query Builder

Genera queries optimizadas para métricas de tipo ratio anual (YTD).
Ejemplo: Tasa de Rotación Anual = Ceses Acumulados / HC Promedio

Estrategia:
1. Un CTE simple que calcula numerador y denominador
2. SELECT final que aplica la fórmula del ratio
3. Solo 15-20 líneas de SQL (vs 80+ líneas del CTE template)
"""

from typing import List, Dict, Any
from app.core.analytics.registry import METRICS_REGISTRY, DIMENSIONS_REGISTRY
from app.core.config.config import get_settings
from app.services.query_builders.utils import build_where_clauses

settings = get_settings()
CUBE_SOURCE = f"`{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`"


def build_ytd_ratio_query(
    metrics: List[str],
    dimensions: List[str],
    filters: Dict[str, Any],
    limit: int = 5000,
    adhoc_groups: List[Any] = None  # NUEVO
) -> str:
    """
    Genera query optimizada para métricas YTD (ratios anuales).
    
    Args:
        metrics: Lista de métricas a calcular
        dimensions: Lista de dimensiones para agrupar (sin 'mes' para YTD)
        filters: Filtros a aplicar
        limit: Límite de resultados
        adhoc_groups: Grupos dinámicos
    
    Returns:
        str: SQL optimizado
    """
    
    # Pre-procesar grupos ad-hoc
    adhoc_map = {}
    if adhoc_groups:
        for grp in adhoc_groups:
            dim = getattr(grp, "dimension", None) or grp.get("dimension")
            if dim:
                adhoc_map[dim] = grp

    # Separar métricas por tipo
    ytd_metrics = []
    simple_metrics = []
    
    for metric_key in metrics:
        metric_def = METRICS_REGISTRY.get(metric_key, {})
        complexity = metric_def.get('complexity', 'simple')
        
        if complexity == 'ytd_ratio':
            ytd_metrics.append(metric_key)
        else:
            simple_metrics.append(metric_key)
    
    # Construir SELECT del CTE (agregaciones base)
    cte_select = []
    final_select = []
    
    # Dimensiones de agrupación (sin temporales para YTD)
    group_dims = [d for d in dimensions if d not in ['mes', 'periodo', 'month']]
    
    # Agregar dimensiones al SELECT
    for dim_key in group_dims:
        dim_def = DIMENSIONS_REGISTRY[dim_key]
        base_col_sql = dim_def.get("sql", dim_key) if isinstance(dim_def, dict) else dim_key
        
        # --- AD-HOC LOGIC ---
        if dim_key in adhoc_map:
            grp = adhoc_map[dim_key]
            label = getattr(grp, "label", None) or grp.get("label")
            values = getattr(grp, "values", None) or grp.get("values")
            vals_str = ", ".join([f"'{v}'" for v in values])
            col_sql = f"CASE WHEN {base_col_sql} IN ({vals_str}) THEN '{label}' ELSE {base_col_sql} END"
        else:
            col_sql = base_col_sql
        # --------------------

        cte_select.append(f"{col_sql} AS {dim_key}")
        final_select.append(dim_key)
    
    # Procesar métricas YTD
    for metric_key in ytd_metrics:
        metric_def = METRICS_REGISTRY[metric_key]
        
        # Obtener numerador y denominador
        num_sql = metric_def['numerator']['sql']
        den_sql = metric_def['denominator']['sql']
        
        # Agregar al CTE
        cte_select.append(f"{num_sql} AS {metric_key}_num")
        cte_select.append(f"{den_sql} AS {metric_key}_den")
        
        # Construir fórmula para SELECT final
        formula = metric_def['formula']
        formula = formula.replace('numerator', f'{metric_key}_num')
        formula = formula.replace('denominator', f'{metric_key}_den')
        
        final_select.append(f"{formula} AS {metric_key}")
    
    # Procesar métricas simples
    for metric_key in simple_metrics:
        metric_def = METRICS_REGISTRY[metric_key]
        sql = metric_def.get('sql', metric_key)
        
        cte_select.append(f"{sql} AS {metric_key}")
        final_select.append(metric_key)
    
    # Construir WHERE
    where_clauses = build_where_clauses(filters, CUBE_SOURCE)
    where_block = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Construir GROUP BY
    group_by = f"GROUP BY {', '.join(group_dims)}" if group_dims else ""
    
    # Ensamblar SQL
    cte_select_str = ",\n        ".join(cte_select)
    final_select_str = ",\n    ".join(final_select)
    
    # Construir ORDER BY si hay un límite pequeño (Top N)
    order_by = ""
    if limit and limit < 5000:
        primary_metric = metrics[0] if metrics else None
        if primary_metric:
            order_by = f"\nORDER BY {primary_metric} DESC"
    
    sql = f"""
WITH yearly_aggregates AS (
    SELECT 
        {cte_select_str}
    FROM {CUBE_SOURCE}
    WHERE {where_block}
    {group_by}
)
SELECT 
    {final_select_str}
FROM yearly_aggregates{order_by}
LIMIT {limit}
"""
    
    return sql.strip()


