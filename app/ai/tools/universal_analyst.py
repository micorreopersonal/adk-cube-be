from typing import List, Dict, Any, Optional, Union
from app.services.bigquery import get_bq_service
from app.services.query_generator import build_analytical_query
from app.schemas.analytics import SemanticRequest
from app.schemas.payloads import (
    VisualDataPackage, KPIBlock, ChartBlock, TableBlock, 
    KPIItem, ChartPayload, Dataset, ChartMetadata, TablePayload
)
from app.core.analytics.registry import METRICS_REGISTRY, DIMENSIONS_REGISTRY
import pandas as pd
import json

# --- CONSTANTS ---
MONTH_MAP = {
    "1": "ene", "2": "feb", "3": "mar", "4": "abr",
    "5": "may", "6": "jun", "7": "jul", "8": "ago",
    "9": "sep", "10": "oct", "11": "nov", "12": "dic"
}

# --- HELPER FUNCTIONS ---

def _format_kpi_block(df: pd.DataFrame, metrics: List[str]) -> KPIBlock:
    """Transforma una fila de resultados en bloque de KPIs."""
    items = []
    if not df.empty:
        row = df.iloc[0]
        for m_key in metrics:
            if m_key in df.columns:
                reg = METRICS_REGISTRY.get(m_key, {})
                val = row[m_key]
                items.append(KPIItem(
                    label=reg.get("label", m_key),
                    value=val, # El frontend maneja el formato si es numero
                    tooltip=reg.get("description"),
                    status="NEUTRAL" # Logica de alertas pendiente
                ))
    return KPIBlock(payload=items)

def _format_chart_block(df: pd.DataFrame, req: SemanticRequest) -> ChartBlock:
    """Transforma un DF en estructura Chart.js."""
    
    # 1. Definir Ejes
    # X Axis = Primera dimensión solicitada
    x_dim = req.cube_query.dimensions[0] if req.cube_query.dimensions else "index"
    
    # Grouping = Segunda dimensión (si existe)
    group_dim = req.cube_query.dimensions[1] if len(req.cube_query.dimensions) > 1 else None
    
    # 2. Generar Datasets
    labels = []
    datasets = []
    
    if group_dim:
        # MODO A: AGRUPADO (Multi-Series por una Dimensión, solo 1ra métrica)
        # Respetamos el orden que viene de SQL para las etiquetas únicas
        raw_labels = df[x_dim].astype(str).unique().tolist()
        
        # Mapeo de meses si corresponde
        if x_dim == "mes":
            labels = [MONTH_MAP.get(lbl, lbl) for lbl in raw_labels]
        else:
            labels = raw_labels
            
        # Generar un dataset por cada grupo
        raw_groups = df[group_dim].unique().tolist()
        # Ordenar grupos (importante para que la leyenda sea consistente)
        try:
            # Intentar orden numérico si es posible
            raw_groups.sort(key=lambda x: float(x) if str(x).replace('.','',1).isdigit() else str(x))
        except:
            raw_groups.sort(key=str)
        
        for g_val in raw_groups:
            subset = df[df[group_dim] == g_val]
            data_points = []
            for lbl in raw_labels: # Usamos raw_labels para buscar en el DF
                match = subset[subset[x_dim].astype(str) == lbl]
                if not match.empty:
                    y_val = match.iloc[0][req.cube_query.metrics[0]]
                else:
                    y_val = 0
                data_points.append(y_val)
            
            # Mapear label del dataset si es mes
            ds_label = MONTH_MAP.get(str(g_val), str(g_val)) if group_dim == "mes" else str(g_val)
            
            # Extraer formato de la métrica desde el registry
            metric_format = None
            if req.cube_query.metrics:
                metric_def = METRICS_REGISTRY.get(req.cube_query.metrics[0], {})
                if "format" in metric_def and isinstance(metric_def["format"], dict):
                    from app.schemas.payloads import MetricFormat
                    metric_format = MetricFormat(**metric_def["format"])
            
            datasets.append(Dataset(label=ds_label, data=data_points, format=metric_format))
            
    else:
        # MODO B: MULTI-MÉTRICA (Múltiples métricas como series independientes)
        raw_labels = df[x_dim].astype(str).tolist() if not df.empty else []
        
        # Mapeo de meses si corresponde
        if x_dim == "mes":
            labels = [MONTH_MAP.get(lbl, lbl) for lbl in raw_labels]
        else:
            labels = raw_labels
            
        for m_key in req.cube_query.metrics:
            if m_key in df.columns:
                m_label = METRICS_REGISTRY.get(m_key, {}).get("label", m_key)
                data_points = df[m_key].tolist()
                
                # Extraer formato de la métrica
                metric_format = None
                metric_def = METRICS_REGISTRY.get(m_key, {})
                if "format" in metric_def and isinstance(metric_def["format"], dict):
                    from app.schemas.payloads import MetricFormat
                    metric_format = MetricFormat(**metric_def["format"])
                
                datasets.append(Dataset(label=m_label, data=data_points, format=metric_format))

    # 3. Metadata
    # Obtener el label de la primera métrica para el eje Y
    metric_label = "Valor"
    if req.cube_query.metrics:
        metric_label = METRICS_REGISTRY.get(req.cube_query.metrics[0], {}).get("label", "Valor")

    meta = ChartMetadata(
        title=req.metadata.title_suggestion or "Análisis de Datos",
        y_axis_label=metric_label,
        show_legend=True
    )
    
    return ChartBlock(
        subtype="BAR" if req.metadata.requested_viz == "BAR_CHART" else "LINE",
        payload=ChartPayload(labels=labels, datasets=datasets),
        metadata=meta
    )

def _format_table_block(df: pd.DataFrame) -> TableBlock:
    """Transforma DF en Tabla (Formato Records para compatibilidad Schema)."""
    # Serializar a Records (List[Dict]) para evitar problemas de arrays anidados
    records = json.loads(df.to_json(orient="records", date_format="iso"))
    return TableBlock(
        payload=TablePayload(
            headers=df.columns.tolist(),
            rows=records
        )
    )

# --- MAIN EXECUTOR ---

def execute_semantic_query(
    intent: str, 
    cube_query: Dict[str, Any], 
    metadata: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Herramienta Maestra (Nexus v2.1).
    Ejecuta consultas analíticas y retorna VisualDataPackage.
    """
    import time
    t_start = time.time()
    timing = {}
    
    try:
        t_step = time.time()
        # A. Resilience Layer: Corregir variaciones comunes del LLM antes de Pydantic
        if metadata and "requested_viz" in metadata:
            viz = str(metadata["requested_viz"]).upper()
            mapping = {
                "LINE": "LINE_CHART",
                "BAR": "BAR_CHART",
                "KPI": "KPI_ROW",
                "GRAPH": "LINE_CHART",
                "CHART": "SMART_AUTO"
            }
            if viz in mapping:
                metadata["requested_viz"] = mapping[viz]

        # 1. Parsear Request v2.1
        full_payload = {
            "intent": intent,
            "cube_query": cube_query,
            "metadata": metadata or {}
        }
        
        # --- BUSINESS RULE: HARD DEFAULT FOR LISTINGS ---
        # Si el usuario pide lista y el LLM olvida el filtro de estado, asumimos 'Cesado'
        # Evita mostrar activos por error en análisis de rotación.
        import logging
        logger = logging.getLogger("universal_analyst")
        
        logger.info(f"🔍 [TRACE] Intent recibido: {intent}")
        logger.info(f"🔍 [TRACE] Filters ANTES de inyección: {cube_query.get('filters', [])}")
        
        if intent == "LISTING":
            filters = cube_query.get("filters", [])
            # Verificamos si existe filtro de 'estado' o sinónimos
            has_state = any(str(f.get("dimension","")).lower() in ["estado", "status", "situacion"] for f in filters)
            logger.info(f"🔍 [TRACE] Intent es LISTING. has_state={has_state}")
            if not has_state:
                filters.append({"dimension": "estado", "value": "Cesado"})
                cube_query["filters"] = filters
                logger.info(f"🔍 [TRACE] ✅ INYECTADO filtro 'Cesado'. Filters DESPUÉS: {filters}")
            else:
                logger.info(f"🔍 [TRACE] ⚠️ Ya existe filtro de estado, no inyectamos")
        else:
            logger.info(f"🔍 [TRACE] Intent NO es LISTING (es: {intent}), saltando inyección")
        # ------------------------------------------------

        req = SemanticRequest(**full_payload)
        
        # 2. Construir SQL Optimizado
        filters_dict = {}
        # --- RESILIENCE: Validar intent ---
        if req.intent not in ["COMPARISON", "TREND", "SNAPSHOT", "LISTING"]:
            raise ValueError(f"Intent inválido: {req.intent}")
        
        # --- SMART LIMITS para LISTING ---
        # Para queries de listado, limitar a 50 registros por defecto para evitar timeouts
        if req.intent == "LISTING" and not limit:
            limit = 50
            logger.info(f"🔍 [TRACE] LISTING query: aplicando límite default de {limit} registros")
        elif limit is None:
            limit = 1000  # Default para queries de métricas
        
        # 2. Generar SQL (usando el Registry para validar dimensiones/métricas)
        for f in req.cube_query.filters:
            if f.dimension in filters_dict:
                current_val = filters_dict[f.dimension]
                if not isinstance(current_val, list):
                    current_val = [current_val]
                if isinstance(f.value, list):
                    current_val.extend(f.value)
                else:
                    current_val.append(f.value)
                filters_dict[f.dimension] = list(set(current_val))
            else:
                filters_dict[f.dimension] = f.value

        # Usamos el limit opcional si viene, si no el default del generador (1000)
        query_params = {
            "metrics": req.cube_query.metrics,
            "dimensions": req.cube_query.dimensions,
            "filters": filters_dict
        }
        if limit:
            query_params["limit"] = limit

        timing['prep'] = time.time() - t_step
        t_step = time.time()
        
        logger.info(f"🔍 [TRACE] Query params enviados a build_analytical_query: {query_params}")
        sql_query = build_analytical_query(**query_params)
        logger.info(f"🔍 [TRACE] SQL generado:\n{sql_query}")
        
        timing['sql_gen'] = time.time() - t_step
        t_step = time.time()
        
        # 3. Ejecutar en BigQuery
        bq = get_bq_service()
        df = bq.execute_query(sql_query)
        
        timing['bq_exec'] = time.time() - t_step
        t_step = time.time()
        logger.info(f"⏱️ [TIMING] BigQuery execution: {timing['bq_exec']:.3f}s")
        
        if df.empty:
            # Retornar paquete vacío (sin content) o con mensaje de error controlado
            return VisualDataPackage(
                summary=f"No se encontraron datos para: {req.metadata.title_suggestion or 'Consulta'}",
                content=[]
            )
        
        # Advertencia si el resultado fue truncado (LISTING queries)
        truncation_warning = None
        if req.intent == "LISTING" and len(df) >= limit:
            truncation_warning = f"⚠️ Mostrando primeros {limit} registros de un total potencialmente mayor. Usa filtros más específicos para acotar los resultados."
            logger.warning(f"LISTING truncado: {len(df)} registros alcanzaron el límite de {limit}")
        
        # 4. Formatear Output según Intención Visual
        blocks = []
        viz_hint = req.metadata.requested_viz
        
        # Lógica de Decisión Visual (Smart Auto)
        if viz_hint == "KPI_ROW" or (viz_hint == "SMART_AUTO" and len(df) == 1):
            blocks.append(_format_kpi_block(df, req.cube_query.metrics))
            
        elif viz_hint in ["LINE_CHART", "BAR_CHART"] or (viz_hint == "SMART_AUTO" and len(df) > 1):
            blocks.append(_format_chart_block(df, req))
            
        elif viz_hint == "TABLE":
            blocks.append(_format_table_block(df))
            
        # 5. Generar Summary (con contador de registros)
        found_count = len(df)
        title_base = req.metadata.title_suggestion or "Análisis de Datos"
        summary = f"{title_base} ({found_count} registros encontrados)"
        
        # Agregar advertencia si fue truncado
        if truncation_warning:
            summary = f"{summary}\n\n{truncation_warning}"
        
        timing['visualization'] = time.time() - t_step
        timing['total'] = time.time() - t_start
        
        logger.info(f"⏱️ [TIMING BREAKDOWN] Total={timing['total']:.3f}s | Prep={timing.get('prep', 0):.3f}s | SQL_Gen={timing.get('sql_gen', 0):.3f}s | BQ_Exec={timing.get('bq_exec', 0):.3f}s | Viz={timing.get('visualization', 0):.3f}s")
        
        # Empaquetar
        pkg = VisualDataPackage(
            summary=summary,
            content=blocks,
            telemetry={
                "model_turns": 1,
                "tools_executed": ["execute_semantic_query"],
                "api_invocations_est": 1
            }
        )

        return pkg.model_dump()
    
    except Exception as e:
        logger.error(f"Error en execute_semantic_query: {e}", exc_info=True)
        return {
            "response_type": "visual_package",
            "summary": f"⚠️ Error procesando consulta: {str(e)}",
            "content": []
        }
