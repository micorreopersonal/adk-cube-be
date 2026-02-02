from typing import Dict, Any, Optional
from app.services.bigquery import get_bq_service
from app.core.config import get_settings
from app.ai.utils.response_builder import ResponseBuilder

settings = get_settings()
bq_service = get_bq_service()

def get_leavers_list(
    periodo: str, 
    uo_level: Optional[str] = "uo2",
    uo_value: Optional[str] = None,
    tipo_rotacion: str = "VOLUNTARIA", 
    segmento: str = "TOTAL",
    **kwargs
) -> Dict[str, Any]:
    """
    Obtiene el listado detallado de personas que cesaron (Leavers) con soporte de UO.
    
    Args:
        periodo: 'YYYY' o 'YYYY-MM'
        uo_level: Nivel organizacional ('uo2', 'uo3')
        uo_value: Nombre de la unidad (ej: 'DIVISION FINANZAS')
        tipo_rotacion: 'VOLUNTARIA' o 'TOTAL'
        segmento: 'FFVV' o 'ADMI'
    """
    dimension = uo_value or kwargs.get("uo_value") or kwargs.get("dimension")
    table_id = f"{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}"
    
    # 1. Filtros de Fecha (Robust Parsing with Quarter Support)
    date_filter = "TRUE"
    if "-Q" in periodo.upper():
        # Formato Quarter: 2025-Q4
        try:
            parts = periodo.upper().split("-Q")
            if len(parts) == 2:
                anio = int(parts[0])
                q_num = int(parts[1])
                
                # Mapeo Q -> Meses
                q_map = {
                    1: (1, 3),   # Ene-Mar
                    2: (4, 6),   # Abr-Jun
                    3: (7, 9),   # Jul-Sep
                    4: (10, 12)  # Oct-Dic
                }
                
                start_m, end_m = q_map.get(q_num, (1, 12))
                date_filter = f"EXTRACT(YEAR FROM fecha_cese) = {anio} AND EXTRACT(MONTH FROM fecha_cese) BETWEEN {start_m} AND {end_m}"
        except ValueError:
            date_filter = "TRUE"

    elif "-" in periodo:
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

    # 4. Filtro de Dimensión Estándar
    dim_filter = ""
    if uo_value:
        col = (uo_level or "uo2").lower()
        dim_filter = f"AND LOWER({col}) LIKE '%{uo_value.lower()}%'"

    query = f"""
    SELECT 
        uo2 as division,
        uo3 as area,
        nombre_completo,
        posicion,
        segmento,
        mapeo_talento_ultimo_anio as mapeo_talento,
        motivo_cese,
        fecha_cese
    FROM `{table_id}`
    WHERE {date_filter}
    {type_filter}
    {seg_filter}
    {dim_filter}
    ORDER BY fecha_cese DESC
    LIMIT 500
    """

    df = bq_service.execute_query(query)
    
    rb = ResponseBuilder()
    
    if df.empty:
        context_unit = f"para **{uo_value}**" if uo_value else "a nivel **Corporativo**"
        rb.add_text(
            f"No se encontraron ceses {context_unit} en {periodo} ({tipo_rotacion}, {segmento}).", 
            variant="standard"
        )
    else:
        count = len(df)
        context_unit = f"para **{uo_value}**" if uo_value else "a nivel **Corporativo**"
        rb.add_text(
            f"Se encontraron **{count}** colaboradores {context_unit} que dejaron la compañía bajo estos criterios.", 
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


def get_leavers_distribution(
    periodo: str, 
    breakdown_by: str, # "UO2", "UO3", "MOTIVO", "POSICION"
    uo_level: Optional[str] = "uo2",
    uo_value: Optional[str] = None,
    tipo_rotacion: str = "TOTAL",
    segmento: str = "TOTAL",
    tipo_talento: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Obtiene la distribución agregada de ceses con soporte de UO.
    
    Args:
        periodo: 'YYYY' o 'YYYY-MM'
        breakdown_by: 'UO2', 'UO3', 'MOTIVO', 'TALENTO'
        uo_level: Nivel organizacional ('uo2', 'uo3')
        uo_value: Nombre de la unidad
        tipo_talento: 'HIPERS', 'HIPOS' o 'TODO_TALENTO'
    """
    dimension = uo_value or kwargs.get("uo_value") or kwargs.get("dimension")
    table_id = f"{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}"
    
    # 1. Mapeo de columnas SQL segun breakdown
    column_map = {
        "UO2": "uo2",
        "DIVISION": "uo2",
        "UO3": "uo3",
        "AREA": "uo3",
        "UO4": "uo4",
        "GERENCIA": "uo4",
        "MOTIVO": "motivo_cese",
        "POSICION": "posicion",
        "SEGMENTO": "segmento",
        "TALENTO": "mapeo_talento_ultimo_anio"
    }
    
    col_sql = column_map.get(breakdown_by.upper(), "uo2")
    label_friendly = breakdown_by.title()

    # 2. Configurar Filtros (Reutilizando lógica similar a leavers list)
    # Fecha
    # Fecha (Robust Parsing with Quarter Support)
    date_filter = "TRUE"
    if "-Q" in periodo.upper():
        try:
            parts = periodo.upper().split("-Q")
            if len(parts) == 2:
                anio = int(parts[0])
                q_num = int(parts[1])
                q_map = { 1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12) }
                start_m, end_m = q_map.get(q_num, (1, 12))
                date_filter = f"EXTRACT(YEAR FROM fecha_cese) = {anio} AND EXTRACT(MONTH FROM fecha_cese) BETWEEN {start_m} AND {end_m}"
        except: pass

    elif "-" in periodo:
        parts = periodo.split("-")
        if len(parts) == 2:
            p1, p2 = parts[0], parts[1]
            if len(p1) == 4: anio, mes = p1, p2
            else: mes, anio = p1, p2
            try:
                date_filter = f"EXTRACT(MONTH FROM fecha_cese) = {int(mes)} AND EXTRACT(YEAR FROM fecha_cese) = {int(anio)}"
            except: pass
    else:
        try:
            date_filter = f"EXTRACT(YEAR FROM fecha_cese) = {int(periodo)}"
        except: pass

    # Tipo (Voluntaria)
    type_filter = ""
    if tipo_rotacion.upper() == "VOLUNTARIA":
        type_filter = "AND LOWER(motivo_cese) LIKE '%renuncia%'"
    
    # Segmento
    seg_filter = ""
    if segmento.upper() == "FFVV":
        seg_filter = "AND segmento = 'EMPLEADO FFVV'"
    elif segmento.upper() in ["ADMINISTRATIVO", "ADMI"]:
        seg_filter = "AND segmento !='EMPLEADO FFVV' AND segmento != 'PRACTICANTE'"
    else:
        seg_filter = "AND segmento != 'PRACTICANTE'"

    # Dimension previa estandarizada
    dim_filter = ""
    if uo_value:
        col = (uo_level or "uo2").lower()
        dim_filter = f"AND LOWER({col}) LIKE '%{uo_value.lower()}%'"

    # --- NUEVO: Filtro de Talento (HU-008) ---
    talento_filter = ""
    talento_label = ""
    if tipo_talento:
        val = str(tipo_talento).upper()
        if "HIPER" in val:
            talento_filter = "AND mapeo_talento_ultimo_anio IN (7)"
            talento_label = " (Hipers)"
        elif "HIPO" in val:
            talento_filter = "AND mapeo_talento_ultimo_anio IN (8, 9)"
            talento_label = " (Hipos)"
        elif "TALENTO" in val or "TODO" in val:
            talento_filter = "AND mapeo_talento_ultimo_anio IN (7, 8, 9)"
            talento_label = " (Talento Clave)"

    # 3. Query de Agregación
    query = f"""
    SELECT 
        {col_sql} as category,
        COUNT(*) as count
    FROM `{table_id}`
    WHERE {date_filter}
    {type_filter}
    {seg_filter}
    {dim_filter}
    {talento_filter}
    GROUP BY 1
    ORDER BY 2 DESC
    LIMIT 20
    """

    df = bq_service.execute_query(query)
    rb = ResponseBuilder()

    if df.empty:
        rb.add_text(f"No se encontraron ceses{talento_label} para distribuir por {label_friendly} en {periodo}.")
        return rb.to_dict()

    # 4. Procesar Data para Chart
    total_count = df['count'].sum()
    chart_data = []
    
    for _, row in df.iterrows():
        val = int(row['count'])
        pct = val / total_count if total_count > 0 else 0
        chart_data.append({
            "label": str(row['category']),
            "value": val,
            "percentage": round(pct, 2)
        })

    # Decidir tipo de gráfico (Si son pocos items, Pie Chart es viable, si son muchos, Bar Chart)
    chart_type = "pie_chart" if len(chart_data) <= 5 else "bar_chart"
    
    context_unit = f"en **{uo_value}**" if uo_value else "a nivel **Corporativo**"
    title = f"Distribución de Ceses{talento_label} por {label_friendly} ({periodo}) {context_unit}"
    rb.add_distribution_chart(
        chart_data, 
        title=title, 
        chart_type=chart_type,
        x_label=label_friendly,
        y_label="N° Ceses"
    )
    
    rb.add_text(
        f"Se analizaron {total_count} salidas de {talento_label.strip() if talento_label else 'colaboradores'}. Mostrando los top {len(chart_data)} grupos.",
        variant="insight", severity="info"
    )
    
    rb.add_debug_sql(query)
    return rb.to_dict()
