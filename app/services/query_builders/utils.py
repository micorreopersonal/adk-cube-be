from typing import List, Dict, Any
from app.core.analytics.registry import DIMENSIONS_REGISTRY

def build_where_clauses(filters: Dict[str, Any], cube_source: str) -> List[str]:
    """
    Construye cláusulas WHERE a partir de filtros vinculados al Registry.
    Soporta la lógica de Periodo Dinámico (MAX) relativo al año si está presente.
    """
    where_clauses = ["segmento != 'PRACTICANTE'"]
    
    if not filters:
        return where_clauses
    
    for dim_key, value in filters.items():
        dim_def = DIMENSIONS_REGISTRY.get(dim_key)
        if not dim_def:
            continue
        
        col_sql = dim_def.get("sql", dim_key) if isinstance(dim_def, dict) else dim_key
        
        # Determinar si es numérico/temporal para evitar LOWER() en el futuro (si se expande)
        is_numeric = False
        if isinstance(dim_def, dict):
            if dim_def.get("sorting") == "numeric" or dim_def.get("type") in ["integer", "float", "number", "numeric", "temporal"]:
                is_numeric = True
        
        def format_val(v):
            if isinstance(v, (int, float)):
                return str(v)
            if isinstance(v, str) and is_numeric and v.replace(".", "", 1).isdigit():
                return v
            return f"'{v}'"
        
        # --- LÓGICA DE PERIODO DINÁMICO (MAX) ---
        if dim_key == "periodo" and isinstance(value, str) and value.upper() == "MAX":
            # Si hay un año en los filtros, el MAX debe ser relativo a ese año
            anio_val = filters.get("anio")
            if anio_val:
                # BigQuery subquery for MAX relative to Year
                where_clauses.append(f"{col_sql} = (SELECT MAX({col_sql}) FROM {cube_source} WHERE anio = {anio_val})")
            else:
                # Global MAX
                where_clauses.append(f"{col_sql} = (SELECT MAX({col_sql}) FROM {cube_source})")
            continue
        # ----------------------------------------

        # Construir condición normal
        if isinstance(value, list):
            vals = ", ".join([format_val(v) for v in value])
            where_clauses.append(f"{col_sql} IN ({vals})")
        else:
            where_clauses.append(f"{col_sql} = {format_val(value)}")
    
    return where_clauses
