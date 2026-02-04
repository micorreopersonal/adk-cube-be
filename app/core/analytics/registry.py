
# Registro central de Verdades de Negocio (Semantic Layer)
# Este archivo define QUÉ medida es válida y CÓMO se calcula.

# -----------------------------------------------------------------------------
# DICCIONARIO DE MÉTRICAS (METRICS STORE)
# -----------------------------------------------------------------------------
METRICS_REGISTRY = {
    "tasa_rotacion": {
        "sql": "SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN estado = 'Cesado' THEN codigo_persona END), COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END)) * 100",
        "label": "Tasa de Rotación Global (%)",
        "description": "Porcentaje de salidas respecto al total de activos en el periodo.",
        "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},
        "type": "ratio"
    },
    "tasa_rotacion_voluntaria": {
        "sql": "SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) LIKE '%renuncia%' THEN codigo_persona END), COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END)) * 100",
        "label": "Tasa de Rotación Voluntaria (%)",
        "description": "Porcentaje de renuncias respecto al total de activos.",
        "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},
        "type": "ratio"
    },
    "tasa_rotacion_involuntaria": {
        "sql": "SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) NOT LIKE '%renuncia%' THEN codigo_persona END), COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END)) * 100",
        "label": "Tasa de Rotación Involuntaria (%)",
        "description": "Porcentaje de despidos/bajas respecto al total de activos.",
        "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},
        "type": "ratio"
    },
    "ceses_totales": {
        "sql": "COUNT(DISTINCT CASE WHEN estado = 'Cesado' THEN codigo_persona END)",
        "label": "Total Ceses",
        "description": "Cantidad absoluta de bajas en el periodo.",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "count"
    },
    "ceses_voluntarios": {
        "sql": "COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) LIKE '%renuncia%' THEN codigo_persona END)",
        "label": "Ceses Voluntarios",
        "description": "Cantidad absoluta de personas que renunciaron.",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "count"
    },
    "ceses_involuntarios": {
        "sql": "COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) NOT LIKE '%renuncia%' THEN codigo_persona END)",
        "label": "Ceses Involuntarios",
        "description": "Cantidad absoluta de personas desvinculadas.",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "count"
    },
    "costo_rotacion": {
        "sql": """
        (
          COUNT(DISTINCT CASE WHEN estado = 'Cesado' THEN codigo_persona END) * 
          (
            -- Costo Estimado: 20% Salario Anual (Proxied via salario_mensual * 12 * 0.2) + Gastos Fijos
            -- Asumimos un salario promedio hardcodeado por seguridad si no hay columna salario real anonimizada
            AVG(CASE WHEN salario_mensual IS NOT NULL THEN salario_mensual ELSE 2500 END) * 2.4 
            + 5000 -- Costo fijo de reclutamiento/capacitación
          )
        )
        """,
        "label": "Costo Estimado de Rotación (USD)",
        "description": "Cálculo aproximado del impacto financiero de las bajas.",
        "format": {"unit_type": "currency", "symbol": "S/", "decimals": 2},
        "type": "currency"
    },
    "headcount_promedio": {
        "sql": """
        (
             (
                SELECT COUNT(DISTINCT codigo_persona) 
                FROM {TABLE} 
                WHERE fecha_corte = DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 MONTH)
                AND estado = 'Activo'
             ) +
             COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END)
        ) / 2
        """,
        "label": "Headcount Promedio",
        "description": "Promedio simple (Inicial + Final) / 2.",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "avg"
    }

}

# -----------------------------------------------------------------------------
# DICCIONARIO DE DIMENSIONES Y FILTROS
# -----------------------------------------------------------------------------
DIMENSIONS_REGISTRY = {
    # Organizacionales
    "uo2": {"sql": "uo2", "category": "organizational", "label": "División"},
    "division": {"sql": "uo2", "category": "organizational", "label": "División"}, # Alias
    "uo3": {"sql": "uo3", "category": "organizational", "label": "Área"},
    "area": {"sql": "uo3", "category": "organizational", "label": "Área"}, # Alias
    "posicion": {"sql": "posicion", "category": "organizational", "label": "Posición"},
    "nombre": {"sql": "nombre_completo", "category": "organizational", "label": "Colaborador"},
    "nombre_completo": {"sql": "nombre_completo", "category": "organizational", "label": "Colaborador"},
    
    # Temporales
    "anio": {"sql": "anio", "category": "temporal", "label": "Año"},
    "mes": {"sql": "EXTRACT(MONTH FROM periodo)", "category": "temporal", "label": "Mes"},
    "trimestre": {"sql": "EXTRACT(QUARTER FROM periodo)", "category": "temporal", "label": "Trimestre"},
    "periodo": {"sql": "periodo", "category": "temporal", "label": "Periodo"},
    "semestre": {"sql": "IF(EXTRACT(MONTH FROM periodo) <= 6, 1, 2)", "category": "temporal", "label": "Semestre"},
    "fecha_cese": {"sql": "fecha_cese", "category": "temporal", "label": "Fecha Cese"},
    
    # Segmentación
    "segmento": {"sql": "segmento", "category": "segmentation", "label": "Segmento"},
    "talento": {"sql": "mapeo_talento_ultimo_anio", "category": "segmentation", "label": "Talento"},
    "motivo": {"sql": "motivo_cese", "category": "segmentation", "label": "Motivo de Cese"},
    "motivo_cese": {"sql": "motivo_cese", "category": "segmentation", "label": "Motivo de Cese"},
    
    # Estado (CRÍTICO para filtros de rotación vs activos)
    "estado": {"sql": "estado", "category": "segmentation", "label": "Estado"},
    
    # Financial / Performance (PER = Penetration Rate)
    # Dato pre-calculado en origen: % penetración vs banda mercado.
    "per_anual": {
        "sql": "per_anual", 
        "category": "financial", 
        "label": "PER Anual (%)"
    },
    "salario": {"sql": "salario_mensual", "category": "segmentation", "label": "Salario Mensual"}
}

# -----------------------------------------------------------------------------
# FILTROS DE SEGURIDAD Y NEGOCIO (WHERE CLAUSES)
# -----------------------------------------------------------------------------
MANDATORY_FILTERS = [
    # Regla de Oro: Excluir practicantes
    "NOT (LOWER(segmento) LIKE '%practicante%')",
]
