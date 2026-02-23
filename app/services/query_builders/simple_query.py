"""
Simple Query Builder

Genera queries para métricas simples (COUNT, SUM, AVG directos).
No requiere CTEs ni Window Functions.

Ejemplo:
- "Total de ceses 2025" → SELECT COUNT(...) FROM cube WHERE anio=2025
- "Ceses por mes 2025" → SELECT mes, COUNT(...) FROM cube WHERE anio=2025 GROUP BY mes
"""

from typing import List, Dict, Any
from app.core.analytics.registry import METRICS_REGISTRY, DIMENSIONS_REGISTRY
from app.core.config.config import get_settings
from app.services.query_builders.utils import build_where_clauses

settings = get_settings()
CUBE_SOURCE = f"`{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`"


def build_simple_query(
    metrics: List[str],
    dimensions: List[str],
    filters: Dict[str, Any],
    limit: int = 5000,
    adhoc_groups: List[Any] = None  # NUEVO
) -> str:
    """
    Genera query simple para métricas de agregación directa.
    
    Args:
        metrics: Lista de métricas a calcular
        dimensions: Lista de dimensiones para agrupar
        filters: Filtros a aplicar
        limit: Límite de resultados
        adhoc_groups: Grupos dinámicos (CASE WHEN)
    
    Returns:
        str: SQL optimizado
    """
    
    # Pre-procesar grupos ad-hoc para búsqueda rápida
    adhoc_map = {}
    if adhoc_groups:
        for grp in adhoc_groups:
            # Soporte para Pydantic o Dict
            dim = getattr(grp, "dimension", None) or grp.get("dimension")
            if dim:
                adhoc_map[dim] = grp

    select_items = []
    group_by_items = []
    
    # Dimensiones
    for dim_key in dimensions:
        if dim_key not in DIMENSIONS_REGISTRY:
            raise ValueError(f"Dimensión no autorizada: '{dim_key}'")
        
        dim_def = DIMENSIONS_REGISTRY[dim_key]
        base_col_sql = dim_def.get("sql", dim_key) if isinstance(dim_def, dict) else dim_key
        
        # Lógica de Ad-Hoc Grouping
        if dim_key in adhoc_map:
            grp = adhoc_map[dim_key]
            label = getattr(grp, "label", None) or grp.get("label")
            values = getattr(grp, "values", None) or grp.get("values")
            
            # Sanitizar valores (asumimos strings por ahora)
            vals_str = ", ".join([f"'{v}'" for v in values])
            
            # Generar CASE WHEN
            # CASE WHEN col IN ('A', 'B') THEN 'Label' ELSE col END
            col_sql = f"CASE WHEN {base_col_sql} IN ({vals_str}) THEN '{label}' ELSE {base_col_sql} END"
        else:
            col_sql = base_col_sql

        select_items.append(f"{col_sql} AS {dim_key}")
        # Para GROUP BY usaremos el alias (posición 1, 2...) o el alias explícito si BigQuery lo soporta
        # En BigQuery standard, GROUP BY {alias} funciona.
        group_by_items.append(dim_key)
    
    # Métricas
    for metric_key in metrics:
        if metric_key not in METRICS_REGISTRY:
            raise ValueError(f"Métrica no definida: '{metric_key}'")
        
        metric_def = METRICS_REGISTRY[metric_key]
        metric_sql = metric_def.get("sql", metric_key)
        select_items.append(f"{metric_sql} AS {metric_key}")
    
    # WHERE
    where_clauses = build_where_clauses(filters, CUBE_SOURCE)
    where_block = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # GROUP BY
    group_by = ""
    if enumerate(group_by_items):
        # Usar índices posicionales (1, 2, 3...) es más robusto a veces, pero alias está bien.
        # Usaremos los aliases definidos en el SELECT.
        group_by = f"GROUP BY {', '.join(group_by_items)}" if group_by_items else ""
    
    # ORDER BY
    order_by = ""
    if dimensions:
        # Ordenar por la primera dimensión (usualmente temporal)
        first_dim = dimensions[0]
        # Si es ad-hoc, ordenamos por el alias
        order_by = f"ORDER BY {first_dim} ASC"
    
    # Ensamblar SQL
    select_str = ",\n    ".join(select_items)
    
    sql = f"""
SELECT 
    {select_str}
FROM {CUBE_SOURCE}
WHERE {where_block}
{group_by}
{order_by}
LIMIT {limit}
"""
    
    return sql.strip()


