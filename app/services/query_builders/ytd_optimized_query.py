"""
Optimized YTD Query Builder

Genera queries optimizadas para métricas YTD que actualmente usan el CTE gigante.
En lugar de 80 líneas con 5 CTEs anidados, genera 20-30 líneas con lógica directa.

Estrategia:
1. Para queries SIN dimensión 'mes': Agregar directamente (SUM, AVG)
2. Para queries CON dimensión 'mes': Usar Window Functions solo donde sea necesario
"""

from typing import List, Dict, Any
from app.core.analytics.registry import METRICS_REGISTRY, DIMENSIONS_REGISTRY
from app.core.config.config import get_settings

settings = get_settings()
CUBE_SOURCE = f"`{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`"


def build_ytd_optimized_query(
    metrics: List[str],
    dimensions: List[str],
    filters: Dict[str, Any],
    limit: int = 5000,
    adhoc_groups: List[Any] = None  # NUEVO
) -> str:
    """
    Genera query optimizada para métricas YTD.
    
    Si NO hay dimensión 'mes': Query simple con agregaciones directas
    Si SÍ hay dimensión 'mes': Query con Window Functions mínimas
    
    Args:
        metrics: Lista de métricas a calcular
        dimensions: Lista de dimensiones para agrupar
        filters: Filtros a aplicar
        limit: Límite de resultados
        adhoc_groups: Grupos dinámicos
    
    Returns:
        str: SQL optimizado
    """
    
    has_mes = "mes" in dimensions or "periodo" in dimensions
    
    # Lista de métricas complejas que REQUIEREN cálculo mensual y luego promedio (no se pueden hacer directo)
    complex_avg_metrics = ["headcount_promedio_acumulado", "tasa_rotacion_anual"]
    requires_monthly_granularity = any(m in metrics for m in complex_avg_metrics)
    
    if not has_mes and not requires_monthly_granularity:
        # Sin dimensión mes y métricas simples → Query simple super rápida
        return _build_ytd_snapshot_query(metrics, dimensions, filters, limit, adhoc_groups)
    else:
        # Con dimensión mes O métricas complejas → Usar CTE (Series Query)
        # CRITICAL FIX: Si el usuario NO pidió 'mes', pero necesitamos 'mes' para el window function,
        # inyectamos 'mes' en la query interna y luego lo excluimos en el wrapper
        query_dimensions = list(dimensions)
        if not has_mes:
            query_dimensions.append("mes")
        
        series_sql = _build_ytd_series_query(metrics, query_dimensions, filters, limit=None, adhoc_groups=adhoc_groups) # Sin limit interno
        
        # Separar la CTE del SELECT para poder envolver la query
        # El formato esperado es "WITH ... \n\nSELECT ..."
        parts = series_sql.split("\n\nSELECT", 1)
        
        if len(parts) == 2:
            cte_part = parts[0]
            select_part = f"SELECT{parts[1]}"
        else:
            # Fallback por si el formato cambia (aunque no debería)
            cte_part = ""
            select_part = series_sql
        
        if has_mes:
            # Si pidió mes, devolver la serie completa
            return series_sql + (f" LIMIT {limit}" if limit else "")
        else:
            # Si NO pidió mes pero era compleja, tomar el último valor acumulado
            # Colocamos la CTE al principio (BigQuery no permite WITH dentro de subquery)
            wrapper_sql = f"""
{cte_part}

SELECT * EXCEPT(mes, rn)
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY {', '.join(dimensions) if dimensions else '1'} ORDER BY mes DESC) as rn
    FROM (
{select_part}
    )
)
WHERE rn = 1
LIMIT {limit}
"""
            return wrapper_sql.strip()



def _build_ytd_snapshot_query(
    metrics: List[str],
    dimensions: List[str],
    filters: Dict[str, Any],
    limit: int,
    adhoc_groups: List[Any] = None  # NUEVO
) -> str:
    """
    Query optimizada para métricas YTD sin desglose mensual.
    Retorna un solo valor acumulado del año.
    
    Ejemplo: "Tasa rotación anual 2025" → 1 fila con el valor YTD
    """
    
    # Pre-procesar grupos ad-hoc
    adhoc_map = {}
    if adhoc_groups:
        for grp in adhoc_groups:
            dim = getattr(grp, "dimension", None) or grp.get("dimension")
            if dim:
                adhoc_map[dim] = grp

    select_items = []
    
    # Dimensiones de agrupación (sin temporales)
    group_dims = [d for d in dimensions if d not in ['mes', 'periodo', 'month']]
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

        select_items.append(f"{col_sql} AS {dim_key}")
    
    # Métricas YTD
    for metric_key in metrics:
        metric_def = METRICS_REGISTRY.get(metric_key, {})
        
        if "tasa_rotacion_anual" in metric_key:
            # Tasa de rotación anual = Ceses totales / HC promedio
            # IMPORTANTE: No podemos usar AVG(CASE WHEN...) porque calcula promedio de 1s y 0s
            # Necesitamos calcular el promedio de headcount mensual
            # Para queries sin dimensión mes, usamos una aproximación:
            # Total ceses / (Total activos / 12 meses)
            
            if "voluntaria" in metric_key:
                num_sql = "COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) LIKE '%renuncia%' THEN codigo_persona END)"
            elif "involuntaria" in metric_key:
                num_sql = "COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) NOT LIKE '%renuncia%' THEN codigo_persona END)"
            else:
                num_sql = "COUNT(DISTINCT CASE WHEN estado = 'Cesado' THEN codigo_persona END)"
            
            # Para el denominador, necesitamos el headcount promedio mensual
            # Como no tenemos dimensión mes, usamos un enfoque simplificado:
            # Contar activos únicos y dividir por número de meses en el periodo
            den_sql = "(COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END) / COUNT(DISTINCT EXTRACT(MONTH FROM periodo)))"
            
            select_items.append(f"SAFE_DIVIDE({num_sql}, {den_sql}) * 100 AS {metric_key}")
        
        elif metric_key in ["ceses_totales", "ceses_voluntarios", "ceses_involuntarios"]:
            # Métricas simples - usar columnas ya calculadas en la CTE, NO el SQL del Registry
            # porque el Registry usa 'estado' que no existe en la CTE
            if metric_key == "ceses_totales":
                select_items.append("ceses AS ceses_totales")
            elif metric_key == "ceses_voluntarios":
                select_items.append("ceses_voluntarios")
            elif metric_key == "ceses_involuntarios":
                select_items.append("ceses_involuntarios")
        

        
        else:
            # Otras métricas YTD (headcount, etc.)
            metric_sql = metric_def.get("sql", metric_key)
            select_items.append(f"{metric_sql} AS {metric_key}")
    
    # WHERE
    where_clauses = _build_where_clauses(filters)
    where_block = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # GROUP BY (solo si hay dimensiones no-temporales)
    group_by = ""
    order_by = ""
    if group_dims:
        dim_cols = []
        for dim_key in group_dims:
            dim_def = DIMENSIONS_REGISTRY[dim_key]
            col_sql = dim_def.get("sql", dim_key) if isinstance(dim_def, dict) else dim_key
            dim_cols.append(col_sql)
        group_by = f"GROUP BY {', '.join(dim_cols)}"
        order_by = f"ORDER BY {dim_cols[0]} ASC"
    
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


def _build_ytd_series_query(
    metrics: List[str],
    dimensions: List[str],
    filters: Dict[str, Any],
    limit: int,
    adhoc_groups: List[Any] = None  # NUEVO
) -> str:
    """
    Query optimizada para métricas YTD con desglose mensual.
    Usa Window Functions pero de forma más eficiente que el CTE gigante.
    
    Ejemplo: "Evolución de rotación mensual 2025" → 12 filas (una por mes)
    """
    
    # Por ahora, delegar al CTE builder existente
    # TODO: Optimizar esto en una segunda iteración
    from app.services.cte_builders import build_headcount_base_cte
    
    cte_sql = build_headcount_base_cte(dimensions, filters, adhoc_groups=adhoc_groups)
    
    # Construir SELECT final
    select_items = []
    
    for dim_key in dimensions:
        select_items.append(dim_key)
    
    for metric_key in metrics:
        metric_def = METRICS_REGISTRY.get(metric_key, {})
        
        # Para métricas de ceses, usar columnas de la CTE en lugar del SQL del Registry
        if metric_key == "ceses_totales":
            select_items.append("ceses AS ceses_totales")
        elif metric_key == "ceses_voluntarios":
            select_items.append("ceses_voluntarios")
        elif metric_key == "ceses_involuntarios":
            select_items.append("ceses_involuntarios")
        elif metric_key == "headcount_promedio_acumulado":
            # La CTE ya calcula 'hc_promedio_acumulado', mapearlo correctamente
            select_items.append("hc_promedio_acumulado AS headcount_promedio_acumulado")
        else:
            # Para otras métricas (tasas, headcount), usar el nombre de columna de la CTE
            col_name = metric_def.get("sql", metric_key)
            select_items.append(f"{col_name} AS {metric_key}")
    
    select_str = ",\n    ".join(select_items)
    
    # Filtros POST-CTE
    where_clauses = []
    if filters:
        for dim_key, value in filters.items():
            if dim_key in ["anio", "year"]:
                where_clauses.append(f"anio = {value}" if not isinstance(value, list) else f"anio IN ({', '.join(map(str, value))})")
    
    where_block = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    limit_clause = f"LIMIT {limit}" if limit else ""
    
    sql = f"""
WITH {cte_sql}

SELECT 
    {select_str}
FROM headcount_base
WHERE {where_block}
ORDER BY anio, mes ASC
{limit_clause}
"""

    
    return sql.strip()


def _build_where_clauses(filters: Dict[str, Any]) -> List[str]:
    """Construye cláusulas WHERE a partir de filtros."""
    where_clauses = ["segmento != 'PRACTICANTE'"]
    
    if not filters:
        return where_clauses
    
    for dim_key, value in filters.items():
        dim_def = DIMENSIONS_REGISTRY.get(dim_key)
        if not dim_def:
            continue
        
        col_sql = dim_def.get("sql", dim_key) if isinstance(dim_def, dict) else dim_key
        
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
    
    return where_clauses
