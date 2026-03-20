from typing import List, Dict, Any, Optional, Union
from app.services.bigquery import get_bq_service
from app.services.query_generator import build_analytical_query
from app.schemas.analytics import SemanticRequest
from app.schemas.payloads import (
    VisualDataPackage, KPIBlock, ChartBlock, TableBlock, 
    KPIItem, ChartPayload, Dataset, ChartMetadata, TablePayload,
    MetricFormat
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
                    
                    # Rellenar métricas con NaN (= "no data", not "zero")
                    # NaN → None in JSON → Chart.js breaks line (no point drawn)
                    for m in req.cube_query.metrics:
                        row[m] = float('nan')
                        
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
                if pd.isna(val):
                    val = 0 # Default for explicit KPIs when missing
                
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
    dimensions_present = req.cube_query.dimensions.copy() if req.cube_query.dimensions else []
    
    # Inyectar 'comparison_group' como dimension si existe en el df
    if "comparison_group" in df.columns and "comparison_group" not in dimensions_present:
        dimensions_present.append("comparison_group")

    if dimensions_present:
        x_dim = dimensions_present[0]
    else:
        x_dim = "index"
        if "index" not in df.columns:
            df = df.copy()
            df["index"] = ["Total"] * len(df) if not df.empty else []

    x_meta = DIMENSIONS_REGISTRY.get(x_dim, {})
    group_dim = dimensions_present[1] if len(dimensions_present) > 1 else None
    
    labels = []
    datasets = []
    consumed_as_informative = set() # Track metrics used as tooltips to avoid redundancy

    # Helper para extraer formato
    def get_format(m_key: str):
        m_def = METRICS_REGISTRY.get(m_key, {})
        if "format" in m_def and isinstance(m_def["format"], dict):
            return MetricFormat(**m_def["format"])
        return None

    # Helper para construir related_datasets
    def get_related(m_key: str, dataframe: pd.DataFrame, filter_col=None, filter_val=None):
        m_def = METRICS_REGISTRY.get(m_key, {})
        info_keys = m_def.get("informative_metrics", [])
        related = []
        for i_key in info_keys:
            if i_key in dataframe.columns:
                i_def = METRICS_REGISTRY.get(i_key, {})
                
                # Si estamos en modo agrupado, el dataframe ya es un subset
                i_data = dataframe[i_key].tolist()
                
                related.append(Dataset(
                    label=i_def.get("label", i_key),
                    data=i_data,
                    format=get_format(i_key)
                ))
                consumed_as_informative.add(i_key)
        return related if related else None

    # 2. Generar Datasets
    if group_dim:
        # MODO A: AGRUPADO (Multi-Series por una Dimensión, solo 1ra métrica)
        raw_labels = df[x_dim].astype(str).unique().tolist()
        
        if x_meta.get("label_mapping"):
            mapping = x_meta["label_mapping"]
            labels = [mapping.get(str(lbl), lbl) for lbl in raw_labels]
        else:
            labels = ["Sin Especificar" if lbl == "None" or lbl == "nan" else lbl for lbl in raw_labels]
            
        raw_groups = df[group_dim].unique().tolist()
        group_meta = DIMENSIONS_REGISTRY.get(group_dim, {})
        
        # Sort groups logically
        try:
            raw_groups.sort(key=lambda x: float(x) if str(x).replace('.','',1).isdigit() else str(x))
        except:
            raw_groups.sort(key=str)
        
        metric_key = req.cube_query.metrics[0] if req.cube_query.metrics else df.columns[0]
        
        for g_val in raw_groups:
            # Subset para este grupo
            subset = df[df[group_dim] == g_val].copy()
            
            # Asegurar alineación con labels del eje X
            data_points = []
            for lbl in raw_labels:
                match = subset[subset[x_dim].astype(str) == lbl]
                data_points.append(match.iloc[0][metric_key] if not match.empty else None)
            
            ds_label = str(g_val)
            if group_meta.get("label_mapping"):
                ds_label = group_meta["label_mapping"].get(str(g_val), str(g_val))
            
            # En modo agrupado, related_datasets se aplica a la misma métrica pero filtrada por grupo
            # Rebalanceamos el subset para que coincida con raw_labels para las métricas informativas
            balanced_subset = []
            for lbl in raw_labels:
                match = subset[subset[x_dim].astype(str) == lbl]
                if not match.empty:
                    balanced_subset.append(match.iloc[0])
                else:
                    # Fill with NaN for missing data points (not zero)
                    row = {col: float('nan') for col in subset.columns}
                    row[x_dim] = lbl
                    balanced_subset.append(pd.Series(row))
            
            df_balanced = pd.DataFrame(balanced_subset)
            
            datasets.append(Dataset(
                label=ds_label,
                data=data_points,
                format=get_format(metric_key),
                related_datasets=get_related(metric_key, df_balanced)
            ))
            
    else:
        # MODO B: MULTI-MÉTRICA (Múltiples métricas como series independientes)
        raw_labels = df[x_dim].astype(str).tolist() if not df.empty else []
        labels = [x_meta.get("label_mapping", {}).get(str(lbl), lbl) for lbl in raw_labels]
        if not x_meta.get("label_mapping"):
            labels = ["Sin Especificar" if lbl == "None" or lbl == "nan" else lbl for lbl in labels]

        # Identificar métricas a procesar (Solicitadas + Inyectadas)
        processed_metrics = []
        for m_key in req.cube_query.metrics:
            if m_key in df.columns:
                processed_metrics.append(m_key)
        for col in df.columns:
            if col in METRICS_REGISTRY and col not in processed_metrics and col not in req.cube_query.dimensions:
                processed_metrics.append(col)

        for m_key in processed_metrics:
            datasets.append(Dataset(
                label=METRICS_REGISTRY.get(m_key, {}).get("label", m_key),
                data=df[m_key].tolist(),
                format=get_format(m_key),
                related_datasets=get_related(m_key, df)
            ))

    # 3. Heuristic: Decluttering (Scale & Focus Management)
    # Si hay Ratios (Tasa), movemos los Counts a tooltips globales solo si no fueron vinculados ya.
    has_ratio = any(ds.format and ds.format.unit_type in ('percentage', 'ratio') for ds in datasets)
    
    final_datasets = []
    tooltip_datasets = []
    
    if has_ratio:
        for ds in datasets:
            # Encontrar el key de la métrica original por su label para saber si fue consumida
            # Nota: Esto es un poco frágil pero efectivo dada la estructura actual.
            m_key = next((k for k, v in METRICS_REGISTRY.items() if v.get("label") == ds.label), ds.label)
            
            if ds.format and ds.format.unit_type in ('percentage', 'ratio'):
                final_datasets.append(ds)
            elif m_key not in consumed_as_informative:
                tooltip_datasets.append(ds)
        
        if final_datasets:
            datasets = final_datasets

    # Metadata
    metric_label = METRICS_REGISTRY.get(req.cube_query.metrics[0], {}).get("label", "Valor") if req.cube_query.metrics else "Valor"
    meta = ChartMetadata(
        title=req.metadata.title_suggestion or "Análisis de Datos",
        y_axis_label=metric_label,
        show_legend=True
    )

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
    elif len(req.cube_query.dimensions) > 0 or "comparison_group" in df.columns:
        if req.cube_query.dimensions:
            x_dim = req.cube_query.dimensions[0]
        else:
            x_dim = "comparison_group"
            
        metric_key = req.cube_query.metrics[0] if req.cube_query.metrics else "count"
        
        # Agrupar valores para evitar duplicados si el DF tiene multiplicidad por comparison_groups
        df_grouped = df.groupby(x_dim, as_index=False)[metric_key].sum()
        raw_labels = df_grouped[x_dim].astype(str).tolist()
        
        # Higiene de Labels
        labels = ["Sin Especificar" if lbl == "None" or lbl == "nan" else lbl for lbl in raw_labels]
        
        data_points = df_grouped[metric_key].tolist()
        
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
    limit: Optional[int] = None,
    comparison_groups: Optional[List[Dict[str, Any]]] = None  # NUEVO
) -> Dict[str, Any]:
    """
    Herramienta Maestra (Nexus v2.1).
    Ejecuta consultas analíticas y retorna VisualDataPackage.
    
    Args:
        intent: Tipo de análisis (TREND, COMPARISON, SNAPSHOT, LISTING)
        cube_query: Query semántica con metrics, dimensions, filters
        metadata: Metadatos adicionales (título, visualización, etc.)
        limit: Límite de resultados
        comparison_groups: (NUEVO) Lista de grupos para comparaciones flexibles.
            Ejemplo: [
                {"label": "2024 Q1", "filters": {"anio": 2024, "trimestre": 1}},
                {"label": "2025 Q1", "filters": {"anio": 2025, "trimestre": 1}}
            ]
    
    Returns:
        Dict con VisualDataPackage
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
        # Permitir límite configurable desde cube_query con validación
        MAX_LISTING_LIMIT = 5000  # Límite máximo de seguridad
        DEFAULT_LISTING_LIMIT = 50  # Límite por defecto
        
        if req.intent == "LISTING":
            if limit:
                # Si se especificó un límite explícito, validarlo
                limit = min(limit, MAX_LISTING_LIMIT)
                logger.info(f"🔍 [TRACE] LISTING query: usando límite solicitado de {limit} registros (max: {MAX_LISTING_LIMIT})")
            else:
                # Límite por defecto
                limit = DEFAULT_LISTING_LIMIT
                logger.info(f"🔍 [TRACE] LISTING query: aplicando límite default de {limit} registros")
        elif limit is None:
            limit = 5000  # Default para queries de métricas
        
        # 2. Generar SQL (usando el Registry para validar dimensiones/métricas)
        for f in req.cube_query.filters:
            # --- STATIC GROUP EXPANSION (Registry) ---
            # Si el valor del filtro coincide con una clave en 'value_groups', expandirlo.
            expanded_values = []
            raw_values = f.value if isinstance(f.value, list) else [f.value]
            
            dim_def = DIMENSIONS_REGISTRY.get(f.dimension, {})

            # [NEW] Normalización de Casing (Force Upper)
            if dim_def.get("force_upper"):
                # Preservar el tipo si no es string, pero si es string, upper
                raw_values = [str(v).upper() if isinstance(v, str) else v for v in raw_values]
                logger.info(f"🔠 [CASE NORM] Normalizando valores de {f.dimension} a UPPERCASE: {raw_values}")

            has_groups = "value_groups" in dim_def
            
            for val in raw_values:
                if has_groups and val in dim_def["value_groups"]:
                    logger.info(f"✨ [GROUP EXPANSION] Expandiendo '{val}' -> {dim_def['value_groups'][val]}")
                    expanded_values.extend(dim_def["value_groups"][val])
                else:
                    expanded_values.append(val)
            
            # Actualizar filters_dict
            if f.dimension in filters_dict:
                current_val = filters_dict[f.dimension]
                if not isinstance(current_val, list):
                    current_val = [current_val]
                current_val.extend(expanded_values)
                filters_dict[f.dimension] = list(set(current_val))
            else:
                # Si es un solo valor y no es lista, mantenerlo simple, sino lista
                if len(expanded_values) == 1:
                    filters_dict[f.dimension] = expanded_values[0]
                else:
                    filters_dict[f.dimension] = list(set(expanded_values))
        
        # --- CONTEXTUAL TITLE GENERATION ---
        # El agente ya incluye contexto en title_suggestion, no duplicar
        base_title = req.metadata.title_suggestion or "Análisis de Datos"
        final_title = base_title  # Usar título del agente sin modificar
        
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
        
        if comparison_groups:
            query_params["comparison_groups"] = comparison_groups

        # --- DYNAMIC AD-HOC GROUPS ---
        # Si el LLM definió grupos ad-hoc, los pasamos al generador
        if hasattr(req.cube_query, "adhoc_groups") and req.cube_query.adhoc_groups:
            query_params["adhoc_groups"] = req.cube_query.adhoc_groups
            
            # También debemos asegurar que los valores del grupo estén permitidos en los filtros
            # (Si no hay filtro explícito, el grupo actúa como filtro implícito)
            for grp in req.cube_query.adhoc_groups:
                if grp.dimension not in filters_dict:
                    logger.info(f"🧩 [AD-HOC FILTER] Aplicando filtro implícito para grupo: {grp.label}")
                    filters_dict[grp.dimension] = grp.values
                else:
                    # Si ya hay filtro, aseguramos que los valores del grupo esten incluidos?
                    # Por ahora asumimos que el filtro explícito manda o ya incluye lo necesario.
                    pass

        # --- AUTO-INJECT INFORMATIVE METRICS (Tooltip Enhancement) ---
        # Si la métrica tiene "informative_metrics" definidos en Registry,
        # los agregamos a la query aunque el usuario no los haya pedido explícitamente.
        # Esto sirve para que el frontend tenga datos de contexto (ej: Denominador en un Ratio).
        
        # 1. Identificar métricas extra necesarias
        extra_metrics = set()
        for m_key in req.cube_query.metrics:
            m_def = METRICS_REGISTRY.get(m_key, {})
            if "informative_metrics" in m_def:
                for info_m in m_def["informative_metrics"]:
                    if info_m not in req.cube_query.metrics:
                        extra_metrics.add(info_m)
        
        # 2. Inyectar en query_params si hay extras
        if extra_metrics:
            logger.info(f"💉 [AUTO-INJECT] Agregando métricas informativas: {extra_metrics}")
            # Importante: Agregamos al final para no alterar el orden de las métricas principales
            # (que determina el color/orden principal del gráfico)
            query_params["metrics"] = req.cube_query.metrics + list(extra_metrics)
        # -------------------------------------------------------------

        timing['prep'] = time.time() - t_step
        t_step = time.time()
        
        logger.info(f"🔍 [TRACE] Query params enviados a build_analytical_query: {query_params}")
        sql_query = build_analytical_query(**query_params)
        logger.info(f"🔍 [TRACE] SQL generado:\n{sql_query}")
        
        timing['sql_gen'] = time.time() - t_step
        t_step = time.time()
        
        
        # 3. Ejecutar en BigQuery con estrategia inteligente para LISTING
        bq = get_bq_service()
        
        # Para LISTING, ejecutar COUNT primero para determinar límite óptimo
        overflow_detected = False
        total_available = None
        
        if req.intent == "LISTING":
            # Paso 1: Ejecutar COUNT para saber cuántos registros hay
            count_sql = sql_query.split("LIMIT")[0]  # Remover LIMIT
            count_sql = f"SELECT COUNT(*) as total FROM ({count_sql}) AS subquery"
            
            try:
                count_df = bq.execute_query(count_sql)
                total_available = int(count_df.iloc[0]['total'])
                logger.info(f"📊 [COUNT] Total de registros disponibles: {total_available}")
                
                # Paso 2: Decidir estrategia según total
                if total_available > 1000:
                    # Caso 1: Más de 1000 → Pedir refinamiento
                    logger.warning(f"⚠️ [OVERFLOW] {total_available} registros encontrados. Requiere refinamiento.")
                    
                    # Retornar mensaje de error amigable
                    pkg = VisualDataPackage(
                        summary=f"🔍 Se encontraron {total_available:,} registros.\n\n"
                                f"⚠️ Esta consulta supera el límite recomendado de 1,000 registros.\n\n"
                                f"💡 **Por favor, refina tu consulta** agregando más filtros específicos:\n"
                                f"   • Filtra por división/área específica\n"
                                f"   • Limita a un periodo más corto (mes, trimestre)\n"
                                f"   • Agrega filtros adicionales (segmento, posición, etc.)\n\n"
                                f"O solicita explícitamente: 'Muestra los primeros 1000 registros'",
                        content=[]
                    )
                    return pkg.model_dump()
                
                elif total_available <= limit:
                    # Caso 2: Menos registros que el límite → Traer todos sin advertencia
                    logger.info(f"✅ [OPTIMAL] {total_available} registros ≤ límite {limit}. Trayendo todos.")
                    df = bq.execute_query(sql_query.replace(f"LIMIT {limit}", f"LIMIT {total_available}"))
                    overflow_detected = False
                
                else:
                    # Caso 3: Entre límite y 1000 → Traer con límite y advertir
                    logger.info(f"⚠️ [PARTIAL] {total_available} registros > límite {limit}. Mostrando primeros {limit}.")
                    df = bq.execute_query(sql_query)
                    overflow_detected = True
                    
            except Exception as e:
                # Si COUNT falla, usar estrategia legacy (LIMIT+1)
                logger.warning(f"⚠️ COUNT query falló: {e}. Usando estrategia legacy.")
                sql_with_overflow = sql_query.replace(f"LIMIT {limit}", f"LIMIT {limit + 1}")
                df = bq.execute_query(sql_with_overflow)
                
                if len(df) > limit:
                    overflow_detected = True
                    df = df.head(limit)
                    total_available = None  # No sabemos el total exacto
        else:
            # Para otros intents, ejecutar normalmente
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
                summary=f"La consulta devolvió 0 casos. No se encontraron datos para: {req.metadata.title_suggestion}",
                content=[]
            )
            return pkg.model_dump()
        
        
        # Advertencia si el resultado fue truncado (LISTING queries)
        truncation_warning = None
        
        # Opción 1: Overflow detectado con COUNT exacto
        if overflow_detected and total_available:
            term = "registros"
            truncation_warning = f"⚠️ Mostrando {len(df)} de {total_available:,} {term} encontrados."
            # Smart Suggestion basado en total
            if total_available <= 200:
                truncation_warning += f"\n💡 Solicita: 'Muestra los {total_available} registros' para ver todos."
            elif total_available <= 1000:
                truncation_warning += f"\n💡 Solicita: 'Muestra {total_available} registros' o refina filtros para ser más específico."
            else:
                truncation_warning += f"\n💡 Refina tus filtros para obtener resultados más específicos."
            logger.warning(f"LISTING truncado: {len(df)} mostrados de {total_available} totales.")
        
        # Opción 2: Overflow detectado sin COUNT exacto (legacy fallback)
        elif overflow_detected:
            term = "registros"
            truncation_warning = f"⚠️ Mostrando {len(df)} de {len(df)}+ {term} encontrados (puede haber más datos)."
            # Smart Suggestion
            if limit < 1000:
                truncation_warning += f"\n💡 Para ver más, solicita: 'Muestra 200 registros' o refina tus filtros para ser más específico."
            else:
                truncation_warning += f"\n💡 Refina tus filtros para obtener resultados más específicos."
            logger.warning(f"LISTING truncado: {len(df)} mostrados, hay más registros disponibles.")
        
        # Opción 3: Si tenemos un conteo total real > filas actuales (otro legacy path)
        elif total_records_found > len(df):
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
        
        # Construir summary según intent
        if req.intent == "LISTING":
            # Para LISTING, summary es solo advertencia/conteo (título ya está en la tabla)
            if truncation_warning:
                # Caso 1: Hay truncamiento → Solo mostrar advertencia
                summary = truncation_warning
            elif total_available:
                # Caso 2: Mostramos todos → Conteo simple
                summary = f"✅ {total_available:,} registros encontrados."
            else:
                # Caso 3: Fallback
                summary = f"✅ {visual_count} registros encontrados."
        else:
            # Para otros intents, usar título completo
            summary = f"{final_title}"
            
            # Resumen de cantidad (solo para no-LISTING)
            if total_available and total_available > visual_count:
                summary += f"\n({visual_count} de {total_available:,} registros)"
            elif total_records_found > visual_count:
                summary += f"\n({visual_count} listados de {total_records_found} totales)"
            
            # Agregar advertencia si existe
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
