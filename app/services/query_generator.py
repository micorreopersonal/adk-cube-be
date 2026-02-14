
from typing import List, Dict, Any, Optional, Set
from app.core.analytics.registry import METRICS_REGISTRY, DIMENSIONS_REGISTRY, MANDATORY_FILTERS
from app.core.config.config import get_settings

settings = get_settings()

# Nombre de la Vista/Tabla Maestra (Cubo Virtual)
# En un entorno real, esto sería una Vista Materializada o una Tabla particionada.
CUBE_SOURCE = f"`{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`"


def _detect_required_ctes(metrics: List[str]) -> Set[str]:
    """
    Detecta qué CTEs son necesarios basándose en las métricas solicitadas.
    
    Args:
        metrics: Lista de métricas solicitadas
        
    Returns:
        Set de nombres de CTEs requeridos
    """
    required_ctes = set()
    
    for metric_key in metrics:
        if metric_key in METRICS_REGISTRY:
            metric_def = METRICS_REGISTRY[metric_key]
            if "requires_cte" in metric_def:
                required_ctes.add(metric_def["requires_cte"])
    
    return required_ctes


def build_analytical_query(
    metrics: List[str],
    dimensions: List[str],
    filters: Optional[Dict[str, Any]] = None,
    comparison_groups: Optional[List[Dict[str, Any]]] = None,
    limit: int = 5000,
    adhoc_groups: Optional[List[Any]] = None  # NUEVO: Grupos dinámicos
) -> str:
    """
    Dispatcher inteligente que elige el builder óptimo según complejidad de métricas.
    
    Args:
        metrics: Lista de métricas a calcular
        dimensions: Lista de dimensiones para agrupar
        filters: Filtros a aplicar
        comparison_groups: Lista de grupos para comparaciones flexibles
        limit: Límite de resultados
        adhoc_groups: (NUEVO) Grupos dinámicos definidos por el usuario/LLM
    
    Returns:
        str: SQL optimizado
    """
    
    # Si hay comparison_groups, verificar si requieren CTE
    # Nota: Por ahora adhoc_groups NO se soportan en comparison_groups (complejidad alta)
    if comparison_groups:
        requires_cte = any(
            METRICS_REGISTRY.get(m, {}).get("requires_cte") or 
            METRICS_REGISTRY.get(m, {}).get("complexity") == "window_function"
            for m in metrics
        )
        
        if requires_cte:
            from app.services.query_builders.comparison_cte_builder import build_ytd_comparison_with_cte
            return build_ytd_comparison_with_cte(metrics, dimensions, comparison_groups, limit)
        else:
            # Métricas simples → Usar builder de comparaciones directo
            # TODO: Soportar adhoc_groups aquí si es necesario
            return _build_comparison_query(metrics, dimensions, comparison_groups, limit)
    
    
    # Detectar si hay métricas que requieren CTEs
    requires_cte = any(
        METRICS_REGISTRY.get(m, {}).get("requires_cte") or 
        METRICS_REGISTRY.get(m, {}).get("complexity") == "window_function"
        for m in metrics
    )
    
    # Detectar si hay métricas YTD ratio
    has_ytd_ratio = any(
        METRICS_REGISTRY.get(m, {}).get("complexity") == "ytd_ratio"
        for m in metrics
    )
    
    # Elegir builder según complejidad
    if requires_cte:
        # Métricas que requieren Window Functions
        from app.services.query_builders.ytd_optimized_query import build_ytd_optimized_query
        return build_ytd_optimized_query(metrics, dimensions, filters or {}, limit, adhoc_groups=adhoc_groups)
    
    elif has_ytd_ratio:
        # Métricas YTD ratio (numerador/denominador)
        from app.services.query_builders.ytd_ratio_query import build_ytd_ratio_query
        return build_ytd_ratio_query(metrics, dimensions, filters or {}, limit, adhoc_groups=adhoc_groups)
    
    else:
        # Métricas simples (COUNT, SUM, AVG directos)
        from app.services.query_builders.simple_query import build_simple_query
        return build_simple_query(metrics, dimensions, filters or {}, limit, adhoc_groups=adhoc_groups)


def _build_cte_query(
    metrics: List[str],
    dimensions: List[str],
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 5000,
    required_ctes: Set[str] = None
) -> str:
    """
    Construye query SQL con CTEs para métricas complejas (Window Functions).
    
    Args:
        metrics: Lista de métricas solicitadas
        dimensions: Lista de dimensiones
        filters: Filtros aplicados
        limit: Límite de filas
        required_ctes: Set de CTEs necesarios
        
    Returns:
        str: SQL completo con CTEs
    """
    from app.services.cte_builders import CTE_BUILDERS
    
    # 1. Generar CTEs necesarios
    cte_sql_parts = []
    for cte_name in required_ctes:
        if cte_name in CTE_BUILDERS:
            builder_func = CTE_BUILDERS[cte_name]
            cte_sql = builder_func(dimensions, filters)
            cte_sql_parts.append(cte_sql)
    
    # 2. Construir SELECT final
    select_items = []
    
    # Mapeo de métricas simples a columnas del CTE headcount_base
    # Cuando usamos CTEs, algunas métricas simples ya están calculadas en el CTE
    CTE_METRIC_MAPPING = {
        "ceses_totales": "ceses",
        "ceses_voluntarios": "ceses_voluntarios",
        "ceses_involuntarios": "ceses_involuntarios"
    }
    
    # Dimensiones
    for dim_key in dimensions:
        if dim_key not in DIMENSIONS_REGISTRY:
            raise ValueError(f"Dimensión no autorizada: '{dim_key}'")
        select_items.append(dim_key)
    
    # Métricas (referencian columnas del CTE)
    for metric_key in metrics:
        if metric_key not in METRICS_REGISTRY:
            raise ValueError(f"Métrica no definida: '{metric_key}'")
        
        metric_def = METRICS_REGISTRY[metric_key]
        
        # Si la métrica tiene requires_cte, usar su definición SQL (que es el nombre de columna)
        if "requires_cte" in metric_def:
            col_name = metric_def["sql"]
            select_items.append(f"{col_name} AS {metric_key}")
        # Si la métrica está en el mapeo, usar la columna del CTE
        elif metric_key in CTE_METRIC_MAPPING:
            col_name = CTE_METRIC_MAPPING[metric_key]
            select_items.append(f"{col_name} AS {metric_key}")
        else:
            # Métrica simple no disponible en CTE - usar definición SQL
            # (Esto podría fallar si la columna no existe en el CTE)
            col_name = metric_def["sql"]
            select_items.append(f"{col_name} AS {metric_key}")
    
    select_block = ",\n    ".join(select_items)
    
    # 3. Construir filtros POST-CTE (filtros temporales que se aplican después de LAG)
    where_clauses = []
    if filters:
        for dim_key, value in filters.items():
            if dim_key in ["anio", "year"]:
                if isinstance(value, list):
                    vals = ", ".join([str(v) for v in value])
                    where_clauses.append(f"anio IN ({vals})")
                else:
                    where_clauses.append(f"anio = {value}")
            elif dim_key in ["mes", "month"]:
                if isinstance(value, list):
                    vals = ", ".join([str(v) for v in value])
                    where_clauses.append(f"mes IN ({vals})")
                else:
                    where_clauses.append(f"mes = {value}")
    
    # CRÍTICO: Si NO hay dimensión 'mes', queremos solo el ÚLTIMO mes (YTD final)
    # Esto es necesario para métricas YTD que acumulan valores mes a mes
    if "mes" not in dimensions:
        # Agregar filtro para obtener solo el mes máximo
        where_clauses.append("mes = (SELECT MAX(mes) FROM headcount_base WHERE anio = headcount_base.anio)")
    
    where_block = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # 4. Ordenamiento
    order_by = "ORDER BY periodo ASC" if "periodo" in dimensions else "ORDER BY anio, mes ASC"
    
    # 5. Ensamblar SQL final
    cte_block = ",\n".join(cte_sql_parts)
    
    sql = f"""
WITH {cte_block}

SELECT 
    {select_block}
FROM headcount_base
WHERE {where_block}
{order_by}
LIMIT {limit}
"""
    
    return sql


def _build_simple_query(
    metrics: List[str],
    dimensions: List[str],
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 5000
) -> str:
    """
    Construye query SQL simple (SELECT + WHERE + GROUP BY).
    Esta es la lógica original de build_analytical_query.
    """
    
    # 1. Validación y Selección de Columnas (SELECT)
    select_items = []
    group_by_indices = []
    
    # Dimensiones (Van primero en el SELECT y en el GROUP BY)
    for i, dim_key in enumerate(dimensions):
        if dim_key not in DIMENSIONS_REGISTRY:
             raise ValueError(f"Dimensión no autorizada o desconocida: '{dim_key}'")
        
        dim_def = DIMENSIONS_REGISTRY[dim_key]
        # Soporte para estructura v2 (Dict) o v1 (Str legacy)
        sql_expr = dim_def["sql"] if isinstance(dim_def, dict) else dim_def
            
        select_items.append(f"{sql_expr} AS {dim_key}")
        group_by_indices.append(str(i + 1)) # SQL indices start at 1

    # --- WINDOW FUNCTION OPTIMIZATION ---
    # Si hay un límite definido (y no es infinito), calculamos el total real de registros
    # que coinciden con los filtros, independientemente del corte.
    if limit and limit > 0:
        select_items.append("COUNT(*) OVER() AS _total_count")
    # ------------------------------------
        
    # Métricas (Agregaciones)
    for metric_key in metrics:
        if metric_key not in METRICS_REGISTRY:
            # Fallback seguro: Si pidieron algo raro, ignorarlo o error? 
            # Mejor error para garantizar "Source of Truth"
            raise ValueError(f"Métrica no definida en Registry: '{metric_key}'")
            
        metric_def = METRICS_REGISTRY[metric_key]
        sql_expr = metric_def["sql"]
        # Inyectar el nombre de la tabla calificado si hay subqueries en la métrica
        if "{TABLE}" in sql_expr:
            sql_expr = sql_expr.replace("{TABLE}", CUBE_SOURCE)
        select_items.append(f"{sql_expr} AS {metric_key}")
        
    # 2. Construcción de Filtros (WHERE)
    where_clauses = list(MANDATORY_FILTERS)  # Copia de filtros base
    
    if filters:
        for dim_key, value in filters.items():
            # Traducir nombre lógico a columna física
            # Si el filtro es sobre una dimensión registrada, usar su definición
            # Si no, asumir columna directa si es seguro (por simplicidad, restringimos a dimensiones conocidas)
            dim_def = DIMENSIONS_REGISTRY.get(dim_key)
            if not dim_def:
                continue
                
            col_sql = dim_def["sql"] if isinstance(dim_def, dict) else dim_def
            
            # Determine if we should apply LOWER() based on metadata
            use_lower = True
            if isinstance(dim_def, dict):
                dim_type = dim_def.get("type", "").lower()
                dim_cat = dim_def.get("category", "").lower()
                # Don't Lower temporal, numeric, boolean, or ratio types
                if dim_type in ["temporal", "numeric", "ratio", "boolean", "integer", "float"] or \
                   dim_cat in ["temporal"]:
                    use_lower = False
            
            if isinstance(value, list):
                # Filtro IN (...)
                clean_values = []
                # Check if values are strings for quoting, but respect column type for LOWER
                
                for v in value:
                    if isinstance(v, str):
                        # If forcing strings on non-lowered column, keep exact value (or assume DB handles coercion)
                        val_str = f"'{v}'" if not v.upper() == "MAX" else v # Handle special cases if any
                        if use_lower:
                            clean_values.append(f"LOWER('{v}')")
                        else:
                            clean_values.append(f"'{v}'")
                    else:
                        clean_values.append(str(v))
                
                list_str = ", ".join(clean_values)
                
                if use_lower:
                    where_clauses.append(f"LOWER({col_sql}) IN ({list_str})")
                else:
                    where_clauses.append(f"{col_sql} IN ({list_str})")
                
            else:
                # Filtro de Igualdad
                if isinstance(value, str):
                    # Caso especial: "MAX" para periodo (último mes cerrado dinámico)
                    if value.upper() == "MAX" and dim_key == "periodo":
                        where_clauses.append(f"{col_sql} = (SELECT MAX({col_sql}) FROM {CUBE_SOURCE})")
                    else:
                        if use_lower:
                            where_clauses.append(f"LOWER({col_sql}) = LOWER('{value}')")
                        else:
                            where_clauses.append(f"{col_sql} = '{value}'")
                else:
                    # Coincidencia Exacta para INT/FLOAT
                    where_clauses.append(f"{col_sql} = {value}")

    # 3. Ensamblaje Final
    select_block = ",\n    ".join(select_items)
    where_block = " AND \n    ".join(where_clauses)
    
    sql = f"""
SELECT 
    {select_block}
FROM {CUBE_SOURCE}
WHERE 
    {where_block}
"""

    # Agregar GROUP BY solo si hay dimensiones Y métricas (agregaciones)
    # Para queries de solo dimensiones (LISTING), NO usar GROUP BY
    if group_by_indices and metrics:
        group_by_block = ", ".join(group_by_indices)
        sql += f"GROUP BY {group_by_block}\n"
        
    # Ordenamiento Inteligente
    if dimensions:
        # Si la primera dimensión es temporal, ordenar ASC por el Eje X (Tendencia)
        first_dim_key = dimensions[0]
        first_dim_def = DIMENSIONS_REGISTRY.get(first_dim_key, {})
        
        if first_dim_def.get("category") == "temporal":
             sql += "ORDER BY 1 ASC\n"
        elif metrics:
             # Si no es temporal, pero hay métricas, ordenar por la 1ra métrica (Ranking/Pareto)
             metric_idx = len(dimensions) + 1
             # If _total_count was injected (limit > 0), the first metric is one pos further
             if limit and limit > 0:
                 metric_idx += 1
             sql += f"ORDER BY {metric_idx} DESC\n"
        else:
             sql += "ORDER BY 1 ASC\n"
    elif metrics:
         # Solo métricas, sin dimensiones → Ordenar por la 1ra métrica
         metric_idx = 1
         if limit and limit > 0:
             metric_idx += 1
         sql += f"ORDER BY {metric_idx} DESC\n"
    
    sql += f"LIMIT {limit}\n"
    
    return sql.strip()


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
    select_clause = ',\n    '.join(select_items)
    sql = f"""
SELECT 
    {select_clause}
FROM {CUBE_SOURCE}
WHERE segmento != 'PRACTICANTE' AND ({where_sql})
GROUP BY {', '.join(group_by_cols)}
ORDER BY {', '.join(order_by_cols)}
LIMIT {limit}
"""
    
    return sql.strip()
