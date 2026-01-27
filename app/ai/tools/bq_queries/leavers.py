from typing import Dict, Any, Optional
from app.services.bigquery import get_bq_service
from app.core.config import get_settings
from app.ai.utils.response_builder import ResponseBuilder

settings = get_settings()
bq_service = get_bq_service()

def get_leavers_list(
    periodo: str, 
    dimension: Optional[str] = None,
    tipo_rotacion: str = "VOLUNTARIA", 
    segmento: str = "TOTAL"
) -> Dict[str, Any]:
    """
    Obtiene el listado detallado de personas que cesaron (Leavers) aplicando filtros estrictos.
    Retorna un VisualDataPackage con una Tabla.

    Args:
        dimension (str): Nivel organizacional (ej. "TECNOLOGIA", "COMERCIAL"). Opcional.
        periodo (str): "YYYY", "MM-YYYY" o "YYYY-MM".
        tipo_rotacion (str): "VOLUNTARIA", "INVOLUNTARIA", "TOTAL".
        segmento (str): "ADMINISTRATIVO", "FFVV", "TOTAL".
    """
    table_id = f"{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}"
    
    # 1. Filtros de Fecha (Robust Parsing)
    date_filter = "TRUE"
    if "-" in periodo:
        parts = periodo.split("-")
        if len(parts) == 2:
            p1, p2 = parts[0], parts[1]
            if len(p1) == 4: # YYYY-MM
                anio, mes = p1, p2
            else: # MM-YYYY
                mes, anio = p1, p2
            
            try:
                date_filter = f"EXTRACT(MONTH FROM fecha_cese) = {int(mes)} AND EXTRACT(YEAR FROM fecha_cese) = {int(anio)}"
            except ValueError:
                date_filter = "TRUE" # Fallback safe
    else:
        # Formato YYYY
        try:
            date_filter = f"EXTRACT(YEAR FROM fecha_cese) = {int(periodo)}"
        except ValueError:
            date_filter = "TRUE"

    # 2. Filtro de Tipo (Voluntaria vs Total)
    type_filter = ""
    if tipo_rotacion.upper() == "VOLUNTARIA":
        type_filter = "AND LOWER(motivo_cese) LIKE '%renuncia%'"
    elif tipo_rotacion.upper() == "INVOLUNTARIA":
        type_filter = "AND LOWER(motivo_cese) NOT LIKE '%renuncia%'"
    
    # 3. Filtro de Segmento
    seg_filter = ""
    if segmento.upper() == "FFVV":
        seg_filter = "AND segmento = 'EMPLEADO FFVV'"
    elif segmento.upper() == "ADMINISTRATIVO" or segmento.upper() == "ADMI":
        seg_filter = "AND segmento != 'EMPLEADO FFVV' AND segmento != 'PRACTICANTE'"
    else:
        # Por defecto (TOTAL) siempre excluimos practicantes
        seg_filter = "AND segmento != 'PRACTICANTE'"

    # 4. Filtro de Dimensión (UO2 - División)
    # Si la dimension es genérica ("General", "Todas", "Total") o None, NO filtramos por UO2.
    dim_filter = ""
    ignored_dims = ["general", "total", "todas", "todo", "company", "compañia", "empresa", "corporativo", "global", "latam"]
    
    if dimension:
        d_lower = dimension.lower()
        # Evitar filtrar si es una palabra ignorada O si es igual al segmento (error común del agente)
        if d_lower not in ignored_dims and d_lower != segmento.lower():
            dim_filter = f"AND LOWER(uo2) LIKE '%{d_lower}%'"

    query = f"""
    SELECT 
        uo2 as division,
        uo3 as area,
        nombre_completo,
        posicion,
        segmento,
        motivo_cese,
        fecha_cese
    FROM `{table_id}`
    WHERE {date_filter}
    {type_filter}
    {seg_filter}
    {dim_filter}
    ORDER BY fecha_cese DESC
    LIMIT 100
    """

    df = bq_service.execute_query(query)
    
    rb = ResponseBuilder()
    
    if df.empty:
        rb.add_text(
            f"No se encontraron ceses para {dimension} en {periodo} ({tipo_rotacion}, {segmento}).", 
            variant="standard"
        )
    else:
        count = len(df)
        rb.add_text(
            f"Se encontraron {count} colaboradores que dejaron la compañía bajo estos criterios.", 
            variant="standard"
        )
        
        # Convertir a lista de dicts para la tabla
        # Serializar fechas para evitar error de Firestore (TypeError: datetime.date)
        if 'fecha_cese' in df.columns:
            df['fecha_cese'] = df['fecha_cese'].astype(str)
            
        records = df.to_dict(orient='records')
        rb.add_table(records)

    # Debug SQL
    rb.add_debug_sql(query)

    return rb.to_dict()
