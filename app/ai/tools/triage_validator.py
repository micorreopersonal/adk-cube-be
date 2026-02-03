from typing import Optional, Dict, Any
from app.services.bigquery import get_bq_service
from app.core.config import get_settings

settings = get_settings()
bq_service = get_bq_service()
table_id = f"{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}"

def validate_dimensions(
    year: Optional[int] = None,
    uo_level: Optional[str] = "uo2",
    uo_value: Optional[str] = None
) -> Dict[str, Any]:
    """
    Herramienta ligera para validar si una Unidad Organizacional existe y si hay datos para un año.
    USAR ÚNICAMENTE DURANTE EL TRIAJE.
    """
    results = {
        "uo_exists": True,
        "uo_official_name": uo_value,
        "has_data_for_year": True,
        "message": ""
    }

    if not uo_value and not year:
        return {"error": "Se requiere al menos un valor para validar."}

    # Validar UO si se proporciona
    if uo_value:
        col_name = (uo_level or "uo2").lower()
        query_uo = f"""
            SELECT DISTINCT {col_name} 
            FROM `{table_id}` 
            WHERE LOWER({col_name}) LIKE '%{uo_value.lower()}%'
            LIMIT 1
        """
        df_uo = bq_service.execute_query(query_uo)
        if df_uo.empty:
            results["uo_exists"] = False
            results["message"] += f"No encontré la unidad '{uo_value}' en el nivel {uo_level}. "
        else:
            results["uo_official_name"] = df_uo.iloc[0][0]

    # Validar Datos del Año si se proporciona
    if year:
        query_year = f"""
            SELECT COUNT(*) as count
            FROM `{table_id}`
            WHERE EXTRACT(YEAR FROM fecha_corte) = {year}
            OR EXTRACT(YEAR FROM fecha_cese) = {year}
            LIMIT 1
        """
        df_year = bq_service.execute_query(query_year)
        count = df_year.iloc[0]['count'] if not df_year.empty else 0
        if count == 0:
            results["has_data_for_year"] = False
            # Consultar y sugerir años disponibles
            query_avail = f"""
                SELECT DISTINCT EXTRACT(YEAR FROM fecha_corte) as y 
                FROM `{table_id}` 
                ORDER BY 1 DESC LIMIT 5
            """
            df_avail = bq_service.execute_query(query_avail)
            avail_years = [str(int(r['y'])) for _, r in df_avail.iterrows()]
            results["message"] += f"No hay datos para el año {year}. Años disponibles: {', '.join(avail_years)}. "

    if not results["message"]:
        results["message"] = "Dimensiones validadas correctamente."
        
    return results

def list_organizational_units(level: str = "uo2", parent_uo: Optional[str] = None) -> Dict[str, Any]:
    """
    Retorna el listado de divisiones (uo2) o áreas (uo3).
    Si se pide uo3, se puede filtrar por una uo2 padre específica (parent_uo).
    """
    col_name = level.lower()
    where_clause = f"{col_name} IS NOT NULL"
    
    if level.lower() == "uo3" and parent_uo:
        where_clause += f" AND LOWER(uo2) LIKE '%{parent_uo.lower()}%'"
        
    query = f"SELECT DISTINCT {col_name} FROM `{table_id}` WHERE {where_clause} ORDER BY 1"
    df = bq_service.execute_query(query)
    
    if df.empty:
        return {"units": [], "message": f"No se encontraron unidades para el nivel {level} (Filtro: {parent_uo or 'Ninguno'})."}
    
    units = df[col_name].tolist()
    return {
        "level": level,
        "parent_filter": parent_uo,
        "total": len(units),
        "units": units,
        "message": f"Se encontraron {len(units)} unidades."
    }
