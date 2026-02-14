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
    where_clauses = _build_where_clauses(filters)
    where_block = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Construir GROUP BY
    group_by = f"GROUP BY {', '.join(group_dims)}" if group_dims else ""
    
    # Ensamblar SQL
    cte_select_str = ",\n        ".join(cte_select)
    final_select_str = ",\n    ".join(final_select)
    
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
FROM yearly_aggregates
LIMIT {limit}
"""
    
    return sql.strip()


def _build_where_clauses(filters: Dict[str, Any]) -> List[str]:
    """Construye cláusulas WHERE a partir de filtros."""
    where_clauses = ["segmento != 'PRACTICANTE'"]
    
    if not filters:
        return where_clauses
    
    for dim_key, value in filters.items():
        # Obtener definición de dimensión
        dim_def = DIMENSIONS_REGISTRY.get(dim_key)
        if not dim_def:
            continue
        
        col_sql = dim_def.get("sql", dim_key) if isinstance(dim_def, dict) else dim_key
        
        # Determinar si es numérico
        is_numeric = False
        if isinstance(dim_def, dict):
            if dim_def.get("sorting") == "numeric" or dim_def.get("type") in ["integer", "float", "number", "numeric"]:
                is_numeric = True
        
        # Formatear valor
        def format_val(v):
            if isinstance(v, (int, float)):
                return str(v)
            if isinstance(v, str) and is_numeric and v.replace(".", "", 1).isdigit():
                return v
            return f"'{v}'"
        
        # Construir condición
        if isinstance(value, list):
            vals = ", ".join([format_val(v) for v in value])
            where_clauses.append(f"{col_sql} IN ({vals})")
        else:
            where_clauses.append(f"{col_sql} = {format_val(value)}")
    
    return where_clauses
