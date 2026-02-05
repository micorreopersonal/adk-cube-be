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
import math

from app.core.analytics.registry import METRICS_REGISTRY, DIMENSIONS_REGISTRY, DEFAULT_FILTERS
import pandas as pd
import json
import math
import logging

logger = logging.getLogger(__name__)

# --- CONSTANTS ---
# (Removed MONTH_MAP, now in Registry)

# --- HELPER FUNCTIONS ---

def _ensure_dataframe_completeness(df: pd.DataFrame, req: SemanticRequest) -> pd.DataFrame:
    """
    Middleware de Completitud: Garantiza que la estructura de datos
    refleje fielmente la intención de comparación del usuario, incluso si
    la base de datos no retorna filas para ciertos periodos/grupos.
    
    Estrategia: 'Zero-Filling' basado en Filtros Explícitos.
    Si el filtro es anio=[2024, 2025] y SQL solo trae 2025, inyectamos 2024=0.
    """
    if not req.cube_query.dimensions:
        return df

    # 1. Identificar Eje Principal (X-Axis)
    x_dim = req.cube_query.dimensions[0] 
    
    # 2. Verificar filtros y Completeness
    if req.cube_query.filters:
        # Verificar si hay una intención explícita de rango/lista en ese eje
        filter_vals = None
        for f in req.cube_query.filters:
            if f.dimension == x_dim:
                filter_vals = f.value
                break
        
        # Si no es una lista, no hay "comparación explícita" que rellenar
        if isinstance(filter_vals, list):
            # 3. Calcular Delta (Lo que esperamos vs Lo que llegó)
            expected_keys = set(str(v) for v in filter_vals)
            
            if df.empty:
                actual_keys = set()
                # Si está vacío, necesitamos inicializar el DF con las columnas correctas
                columns = req.cube_query.dimensions + req.cube_query.metrics
                df = pd.DataFrame(columns=columns)
            else:
                actual_keys = set(df[x_dim].astype(str).unique())
                
            missing_keys = expected_keys - actual_keys
            
            if missing_keys:
                print(f"🧱 [MIDDLEWARE] Data Completeness: Injecting missing keys for {x_dim}: {missing_keys}")
                
                # 4. Inyectar Filas Faltantes (Zero-Filling)
                new_rows = []
                for mis in missing_keys:
                    # Intentar mantener el tipo de dato original si es posible
                    val = int(mis) if str(mis).isdigit() else mis
                    
                    row = {x_dim: val}
                    
                    # Rellenar métricas con 0
                    for m in req.cube_query.metrics:
                        row[m] = 0
                        
                    # Otras dimensiones: "N/A" o Contextual
                    new_rows.append(row)
                
                df_fill = pd.DataFrame(new_rows)
                df = pd.concat([df, df_fill], ignore_index=True)
    
    # 5. Ordenamiento (Crucial para series temporales)
    # Usar metadata del registro si está disponible
    x_meta = DIMENSIONS_REGISTRY.get(x_dim, {})
    if x_meta.get("type") == "temporal" or x_meta.get("sorting") == "numeric":
        # Ordenar numérica o temporalmente
        try:
            df = df.sort_values(by=x_dim)
        except:
            pass
            
    return df

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
    x_meta = DIMENSIONS_REGISTRY.get(x_dim, {})
    
    # Grouping = Segunda dimensión (si existe)
    group_dim = req.cube_query.dimensions[1] if len(req.cube_query.dimensions) > 1 else None
    
    # 2. Generar Datasets
    labels = []
    datasets = []
    
    if group_dim:
        # MODO A: AGRUPADO (Multi-Series por una Dimensión, solo 1ra métrica)
        # Respetamos el orden que viene de SQL para las etiquetas únicas
        raw_labels = df[x_dim].astype(str).unique().tolist()
        
        if x_meta.get("label_mapping"):
            mapping = x_meta["label_mapping"]
            labels = [mapping.get(str(lbl), lbl) for lbl in raw_labels]
        else:
            # Data Hygiene: Replace "None" string from database with user-friendly text
            labels = ["Sin Especificar" if lbl == "None" or lbl == "nan" else lbl for lbl in raw_labels]
            
        # Generar un dataset por cada grupo
        raw_groups = df[group_dim].unique().tolist()
        
        # Ordenar grupos (importante para que la leyenda sea consistente)
        group_meta = DIMENSIONS_REGISTRY.get(group_dim, {})
        try:
            is_numeric = group_meta.get("sorting") == "numeric" or group_meta.get("type") == "temporal"
            if is_numeric:
                 # Intentar orden numérico si es posible
                raw_groups.sort(key=lambda x: float(x) if str(x).replace('.','',1).isdigit() else str(x))
            else:
                raw_groups.sort(key=str)
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
            
            # Mapear label del dataset si tiene mapping (ej: meses como series)
            ds_label = str(g_val)
            if group_meta.get("label_mapping"):
                ds_label = group_meta["label_mapping"].get(str(g_val), str(g_val))
            
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
        
        # Mapeo de valores (ej: meses)
        if x_meta.get("label_mapping"):
            mapping = x_meta["label_mapping"]
            labels = [mapping.get(str(lbl), lbl) for lbl in raw_labels]
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

    # ... (existing Dataset generation above)
    
    # 3. Handle PIE Specifics
    # Si la visualización pedida es PIE_CHART, forzamos un único dataset y estructura simple
    is_pie = req.metadata.requested_viz == "PIE_CHART"
    
    if is_pie:
        # Asegurar colores distintos para cada slice en Pie (Chart.js lo hace auto, pero mejor si es explícito o simple)
        # Por ahora enviamos estructura estándar, el frontend interpretará labels vs data
        pass

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
    
    # Mapeo de subtipo
    subtype_map = {
        "BAR_CHART": "BAR",
        "PIE_CHART": "PIE",
        "LINE_CHART": "LINE"
    }
    subtype = subtype_map.get(str(req.metadata.requested_viz), "LINE")
    
    
    # 4. Heuristic: Decluttering (Scale & Focus Management)
    # If the chart contains "Percentage" metrics (Ratios), hide/exclude "Count" metrics 
    # to avoid plotting distinct counts (e.g. 5, 20) against ratios (5%, 15%) on the same axis.
    # We prefer Ratios as they are usually the primary intent when both are present.
    
    has_ratio = any(
        ds.format and ds.format.unit_type in ('percentage', 'ratio') 
        for ds in datasets
    )
    
    tooltip_datasets = []
    
    if has_ratio:
        primary_datasets = []
        for ds in datasets:
            if ds.format and ds.format.unit_type in ('percentage', 'ratio'):
                primary_datasets.append(ds)
            else:
                # Move Non-Ratio metrics (like Counts) to Tooltip
                tooltip_datasets.append(ds)
        
        # Only switch if we found primary datasets
        if primary_datasets:
            datasets = primary_datasets

    return ChartBlock(
        subtype="BAR" if req.metadata.requested_viz == "BAR_CHART" else "LINE",
        payload=ChartPayload(labels=labels, datasets=datasets, tooltip_datasets=tooltip_datasets),
        metadata=meta
    )

def _format_pie_strategy(df: pd.DataFrame, req: SemanticRequest) -> ChartBlock:
    """
    Estrategia especializada para Gráficos de Torta/Donut.
    Maneja dos modos:
    1. Distribución (Dimensional): 1 Métrica desglosada por 1 Dimensión.
    2. Comparativa (Métrica): N Métricas comparadas entre sí (Transposición).
    """
    labels = []
    data_points = []
    
    # --- MODO COMPARATIVA (Multi-Métrica) ---
    # Prioridad: Si hay >1 métrica, asumimos que se quiere comparar los totales de esas métricas
    # independientemente de si el LLM agregó dimensiones de desglose (que agregaremos con .sum()).
    if len(req.cube_query.metrics) > 1:
        for m_key in req.cube_query.metrics:
            # Label = Nombre legible de la métrica
            m_def = METRICS_REGISTRY.get(m_key, {})
            labels.append(m_def.get("label", m_key))
            # Valor: Suma total de la columna (Robustez ante dimensiones innecesarias)
            val = df[m_key].sum()
            # Convertir numpy types a python nativo si es necesario
            data_points.append(float(val) if hasattr(val, "item") else val)
    
    # --- MODO DISTRIBUCIÓN (Estándar, 1 Métrica + Dimensiones) ---
    # Ej: "Headcount por División"
    elif len(req.cube_query.dimensions) > 0:
        x_dim = req.cube_query.dimensions[0]
        metric_key = req.cube_query.metrics[0] if req.cube_query.metrics else "count"
        
        raw_labels = df[x_dim].astype(str).tolist()
        # Higiene de Labels
        labels = ["Sin Especificar" if lbl == "None" or lbl == "nan" else lbl for lbl in raw_labels]
        
        data_points = df[metric_key].tolist()
        
        # Mapeo de dimensiones (ej: meses)
        x_meta = DIMENSIONS_REGISTRY.get(x_dim, {})
        if x_meta.get("label_mapping"):
             # type check for linter
             mapping = x_meta["label_mapping"]
             labels = [mapping.get(str(lbl), lbl) for lbl in labels]

    # Construir Dataset único
    # NOTA: Chart.js para Pie usa 1 dataset. Los colores son automáticos o definidos en array backgroundColor.
    ds = Dataset(
        label="Distribución",
        data=data_points,
        format=None # Heredar del default o implementar lógica compleja si se requiere
    )
    
    meta = ChartMetadata(
        title=req.metadata.title_suggestion or "Distribución",
        show_legend=True
    )
    
    datasets = [ds] # Initialize list for filtering logic

    # 4. Heuristic: Decluttering (Scale & Focus Management)
    # If the chart contains "Percentage" metrics (Ratios), hide/exclude "Count" metrics 
    # to avoid plotting distinct counts (e.g. 5, 20) against ratios (5%, 15%) on the same axis.
    # We prefer Ratios as they are usually the primary intent when both are present.
    
    has_ratio = any(
        ds.format and ds.format.unit_type in ('percentage', 'ratio') 
        for ds in datasets
    )
    
    tooltip_datasets = []
    
    if has_ratio:
        primary_datasets = []
        for ds in datasets:
            if ds.format and ds.format.unit_type in ('percentage', 'ratio'):
                primary_datasets.append(ds)
            else:
                tooltip_datasets.append(ds)
        
        if primary_datasets:
            datasets = primary_datasets

    return ChartBlock(
        subtype="PIE",
        payload=ChartPayload(labels=labels, datasets=datasets, tooltip_datasets=tooltip_datasets),
        metadata=meta
    )

from app.core.utils.formatting import format_dataframe_for_export
from app.core.auth.security import mask_document_id, mask_salary

def _format_table_block(df: pd.DataFrame, title: str = "Detalle de Datos") -> TableBlock:
    """Transforma DF en Tabla (Formato Records para compatibilidad Schema)."""
    
    records = format_dataframe_for_export(df)
    return TableBlock(
        payload=TablePayload(
            headers=df.columns.tolist(),
            rows=records
        ),
        metadata=ChartMetadata(title=title, show_legend=False)
    )


def _sanitize_payload(obj: Any) -> Any:
    """
    Recursively replaces NaN and Infinity with None to ensure valid JSON for LLM.
    """
    if isinstance(obj, dict):
        return {k: _sanitize_payload(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_payload(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj


def _generate_context_string(filters: Dict[str, Any]) -> str:
    """Genera un string legible de los filtros aplicados para el contexto."""
    parts = []
    
    # Mapeo de nombres legibles para dimensiones comunes
    dim_labels = {
        "uo2": "División",
        "uo3": "Área",
        "anio": "Año",
        "mes": "Mes",
        "periodo": "Periodo",
        "estado": "Estado"
    }
    
    for dim, val in filters.items():
        label = dim_labels.get(dim, dim.capitalize())
        
        # Formatear valor
        if isinstance(val, list):
            val_str = ", ".join(str(v) for v in val)
        elif val == "MAX":
            val_str = "Último Cerrado"
        else:
            val_str = str(val)
            
        parts.append(f"{label}: {val_str}")
        
    if not parts:
        return ""
        
    return " | ".join(parts)

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
                "PIE": "PIE_CHART",
                "TORTA": "PIE_CHART",
                "PASTEL": "PIE_CHART",
                "DONUT": "PIE_CHART",
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
        
        # --- BUSINESS RULE: DEFAULT FILTERS FROM REGISTRY ---
        # Aplicar reglas de negocio definidas en Registry de forma agnóstica
        intent_defaults = DEFAULT_FILTERS.get(intent, [])
        if intent_defaults:
            current_filters = cube_query.get("filters", [])
            for rule in intent_defaults:
                should_apply = True
                # verificar missing conditions
                if "condition_missing" in rule:
                    for dim_check in rule["condition_missing"]:
                         # Chequear si esa dimension ya existe en los filtros actuales
                         if any(str(f.get("dimension","")).lower() == dim_check for f in current_filters):
                             should_apply = False
                             break
                
                if should_apply:
                    logger.info(f"🔍 [TRACE] Aplicando Default Rule: {rule['dimension']}={rule['value']}")
                    current_filters.append({"dimension": rule["dimension"], "value": rule["value"]})
            
            cube_query["filters"] = current_filters
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
        
        # --- CONTEXTUAL TITLE GENERATION ---
        context_str = _generate_context_string(filters_dict)
        base_title = req.metadata.title_suggestion or "Análisis de Datos"
        
        # Si el LLM ya puso contexto en el título, tratamos de no duplicar (heurística simple)
        final_title = base_title
        # Si el contexto es relevante y no parece estar ya en el título, lo agregamos
        if context_str:
             if " | " not in base_title: # Evitar doble barra si el LLM ya lo intentó
                 final_title = f"{base_title} [{context_str}]"
        
        req.metadata.title_suggestion = final_title
        # -----------------------------------

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
        
        # 3.2 Dynamic Comparison Strategy (CUBE LOGIC)
        # Si la intención es COMPARISON, detectamos automágicamente cuál es el Eje de Series.
        # Regla: Si hay un filtro con múltiples valores (ej: anio=[2024, 2025]), esa dimensión es la SERIE.
        if req.intent == "COMPARISON" and len(req.cube_query.dimensions) > 1:
            comparison_dim = None
            # Buscar dimensión con cardinalidad > 1 en los filtros explícitos
            for dim, val in filters_dict.items():
                if isinstance(val, list) and len(val) > 1:
                    comparison_dim = dim
                    break
            
            # Si encontramos una dimensión de comparación y está en las dimensiones solicitadas
            # La movemos al Index 1 (Agrupador/Series), dejando Index 0 como Eje X (ej: Mes)
            if comparison_dim and comparison_dim in req.cube_query.dimensions:
                # Solo reordenar si no son múltiples métricas (Multi-Metric tiene su propia estrategia)
                if len(req.cube_query.metrics) == 1:
                    logger.info(f"🧱 [CUBE] Detectado Eje de Comparación: {comparison_dim}. Reordenando para visualización.")
                    req.cube_query.dimensions.remove(comparison_dim)
                    req.cube_query.dimensions.insert(1, comparison_dim)

        # 3.5 Middleware de Completitud (Arquitectura Escalable)
        # Inyectar ceros para periodos/dimensiones faltantes ANTES de decidir la visualización
        # Esto asegura que 1 registro real + 1 registro zero-filled = 2 registros -> Gráfico (no KPI)
        df = _ensure_dataframe_completeness(df, req)
        
        # --- TOTAL COUNT EXTRACTION ---
        # Extraer el conteo total real (Window Function) antes de que el DF sea consumido
        total_records_found = 0
        if not df.empty and "_total_count" in df.columns:
            total_records_found = int(df.iloc[0]["_total_count"])
            # Limpiar columna auxiliar para que no salga en la tabla
            df = df.drop(columns=["_total_count"])
        elif not df.empty:
            total_records_found = len(df)
        # ------------------------------
        
        if df.empty:
            # Retornar paquete vacío (sin content) o con mensaje de error controlado
            pkg = VisualDataPackage(
                summary=f"No se encontraron datos para: {req.metadata.title_suggestion}",
                content=[]
            )
            return pkg.model_dump()
        
        # Advertencia si el resultado fue truncado (LISTING queries)
        truncation_warning = None
        # Si tenemos un conteo total real > filas actuales
        if total_records_found > len(df):
            term = "registros"
            truncation_warning = f"⚠️ Mostrando {len(df)} de {total_records_found} {term} encontrados."
            # Smart Suggestion para ver todo
            truncation_warning += f"\n💡 Para ver más, intenta ser específico: 'Dame los {total_records_found} registros de...'"
            logger.warning(f"LISTING truncado: {len(df)} mostrados de {total_records_found} totales.")
        
        # 4. Formatear Output según Intención Visual
        blocks = []
        viz_hint = req.metadata.requested_viz
        
        # Lógica de Decisión Visual (Smart Auto)
        if viz_hint == "KPI_ROW" or (viz_hint == "SMART_AUTO" and len(df) == 1):
            blocks.append(_format_kpi_block(df, req.cube_query.metrics))
        
        elif viz_hint == "PIE_CHART":
             blocks.append(_format_pie_strategy(df, req))
            
        elif viz_hint in ["LINE_CHART", "BAR_CHART"] or (viz_hint == "SMART_AUTO" and len(df) > 1):
            blocks.append(_format_chart_block(df, req))
            
        elif viz_hint == "TABLE":
            # Pasar título contextual al bloque de tabla
            blocks.append(_format_table_block(df, title=final_title))
            
        # 5. Generar Summary (con contador de registros)
        visual_count = len(df)
        
        # Usamos el título enriquecido para el summary
        summary = f"{final_title}"
        if context_str and context_str not in summary: # Fallback por si acaso
             summary += f"\nContexto: {context_str}"
        
        # Resumen de cantidad
        if total_records_found > visual_count:
             summary += f"\n({visual_count} listados de {total_records_found} totales)"
        else:
             summary += f"\n({visual_count} registros encontrados)"
        
        # Agregar advertencia detallada
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

        return _sanitize_payload(pkg.model_dump())
    
    except Exception as e:
        logger.error(f"Error en execute_semantic_query: {e}", exc_info=True)
        return {
            "response_type": "visual_package",
            "summary": f"⚠️ Error procesando consulta: {str(e)}",
            "content": []
        }
