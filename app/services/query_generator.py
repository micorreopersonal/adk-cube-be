
from typing import List, Dict, Any, Optional
from app.core.analytics.registry import METRICS_REGISTRY, DIMENSIONS_REGISTRY, MANDATORY_FILTERS
from app.core.config.config import get_settings

settings = get_settings()

# Nombre de la Vista/Tabla Maestra (Cubo Virtual)
# En un entorno real, esto sería una Vista Materializada o una Tabla particionada.
CUBE_SOURCE = f"`{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}`"

def build_analytical_query(
    metrics: List[str],
    dimensions: List[str],
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 1000
) -> str:
    """
    Construye una query SQL segura y optimizada basada en objetos semánticos.
    
    Args:
        metrics: Lista de keys definidas en METRICS_REGISTRY (ej: ['tasa_rotacion', 'headcount_actual'])
        dimensions: Lista de keys definidas en DIMENSIONS_REGISTRY (ej: ['uo2', 'anio'])
        filters: Diccionario de filtros {dimension: valor} o {dimension: [valores]}
        limit: Límite de filas (default 1000)
        
    Returns:
        str: SQL compilado listo para ejecutar en BigQuery.
        
    Raises:
        ValueError: Si una métrica o dimensión no existe en el registro.
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
            
            if isinstance(value, list):
                # Filtro IN (...)
                clean_values = []
                is_string_list = any(isinstance(v, str) for v in value)
                
                for v in value:
                    if isinstance(v, str):
                        clean_values.append(f"LOWER('{v}')")
                    else:
                        clean_values.append(str(v))
                
                list_str = ", ".join(clean_values)
                
                if is_string_list:
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
                        # Coincidencia Exacta para STRINGS (case-insensitive)
                        where_clauses.append(f"LOWER({col_sql}) = LOWER('{value}')")
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
             sql += f"ORDER BY {metric_idx} DESC\n"
        else:
             sql += "ORDER BY 1 ASC\n"
    elif metrics:
        sql += "ORDER BY 1 DESC\n"
        
    sql += f"LIMIT {limit}"
    
    return sql
