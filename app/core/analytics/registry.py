
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
    "uo4": {"sql": "uo4", "category": "organizational", "label": "UO4"},
    "uo5": {"sql": "uo5", "category": "organizational", "label": "UO5"},
    "uo6": {"sql": "uo6", "category": "organizational", "label": "UO6"},
    "posicion": {"sql": "posicion", "category": "organizational", "label": "Posición"},
    "nombre": {"sql": "nombre_completo", "category": "organizational", "label": "Colaborador"},
    "nombre_completo": {"sql": "nombre_completo", "category": "organizational", "label": "Colaborador"},
    
    "supervisor": {"sql": "supervisor", "category": "organizational", "label": "Supervisor"},
    "gerente": {"sql": "gerente", "category": "organizational", "label": "Gerente"},
    "razon_social": {"sql": "razon_social", "category": "segmentation", "label": "Razón Social"},
    "tipo_documento": {"sql": "tipo_documento", "category": "personal", "label": "Tipo Documento"},
    "dni": {"sql": "dni", "category": "personal", "label": "DNI"},
    "fecha_nacimiento": {"sql": "fecha_nacimiento", "category": "personal", "label": "Fecha Nacimiento"},
    "codigo_persona": {"sql": "codigo_persona", "category": "personal", "label": "Código Persona"},
    "nombre_completo_antiguo": {"sql": "nombre_completo_antiguo", "category": "personal", "label": "Nombre Completo Antiguo"},
    "nombres": {"sql": "nombres", "category": "personal", "label": "Nombres"},
    "apellido_paterno": {"sql": "apellido_paterno", "category": "personal", "label": "Apellido Paterno"},
    "apellido_materno": {"sql": "apellido_materno", "category": "personal", "label": "Apellido Materno"},
    "sexo": {"sql": "sexo", "category": "personal", "label": "Sexo"},
    "estado_civil": {"sql": "estado_civil", "category": "personal", "label": "Estado Civil"},
    "nacionalidad": {"sql": "nacionalidad", "category": "personal", "label": "Nacionalidad"},
    
    # Ubicación
    "sede_rimac": {"sql": "sede_rimac", "category": "location", "label": "Sede Rimac"},
    "departamento": {"sql": "departamento", "category": "location", "label": "Departamento"},
    "provincia": {"sql": "provincia", "category": "location", "label": "Provincia"},
    "distrito": {"sql": "distrito", "category": "location", "label": "Distrito"},
    
    # Temporales
    "anio": {
        "sql": "anio", 
        "category": "temporal", 
        "label": "Año",
        "type": "temporal",
        "sorting": "numeric"
    },
    "mes": {
        "sql": "EXTRACT(MONTH FROM periodo)", 
        "category": "temporal", 
        "label": "Mes",
        "type": "temporal",
        "sorting": "numeric",
        "label_mapping": {
            "1": "ene", "2": "feb", "3": "mar", "4": "abr",
            "5": "may", "6": "jun", "7": "jul", "8": "ago",
            "9": "sep", "10": "oct", "11": "nov", "12": "dic"
        }
    },
    "grupo_periodo": {
        "sql": "CONCAT(CAST(EXTRACT(YEAR FROM periodo) AS STRING), 'Q', CAST(EXTRACT(QUARTER FROM periodo) AS STRING))", 
        "category": "temporal", 
        "label": "Trimestre (Q) / Grupo Periodo",
        "description": "Formato 'YYYYQ#' (Ej: 2025Q4). Usar SIEMPRE para filtrar por Trimestres/Cuartiles."
    },
    "trimestre": {"sql": "grupo_periodo", "category": "temporal", "label": "Trimestre (Alias)"},
    "q": {"sql": "grupo_periodo", "category": "temporal", "label": "Trimestre (Alias)"},
    "periodo": {
        "sql": "FORMAT_DATE('%Y%m', periodo)", 
        "category": "temporal", 
        "label": "Periodo (YYYYMM)",
        "description": "Formato Mensual 'YYYYMM' (Ej: 202510). NO USAR para Trimestres."
    },
    "semestre": {"sql": "IF(EXTRACT(MONTH FROM periodo) <= 6, 1, 2)", "category": "temporal", "label": "Semestre"},
    "fecha_cese": {"sql": "fecha_cese", "category": "temporal", "label": "Fecha Cese"},
    "fecha_ingreso": {"sql": "fecha_ingreso", "category": "temporal", "label": "Fecha Ingreso"},
    "anio_ingreso": {"sql": "anio_ingreso", "category": "temporal", "label": "Año Ingreso"},
    "mes_anio_ingreso": {"sql": "mes_anio_ingreso", "category": "temporal", "label": "Mes/Año Ingreso"},
    "ts_anios": {"sql": "ts_anios", "category": "temporal", "label": "Tiempo Servicio (Años)"},
    "ts_dias": {"sql": "ts_dias", "category": "temporal", "label": "Tiempo Servicio (Días)"},
    
    # Segmentación
    # IMPORTANTE: Definiciones de Segmento (Single Source of Truth)
    # - "EMPLEADO FFVV" = Fuerza de Ventas (FFVV)
    # - Todos los demás (excepto PRACTICANTE) = Administrativo (ADMIN)
    # - PRACTICANTE = Excluido por filtro obligatorio
    "segmento": {
        "sql": "segmento",
        "category": "segmentation",
        "label": "Segmento",
        "description": "Segmento de empleado. Valores individuales: EMPLEADO, EMPLEADO FFVV, GERENTE, JEFE, etc.",
        "value_definitions": {
            "EMPLEADO FFVV": "Fuerza de Ventas - Personal de ventas en campo",
            "EMPLEADO": "Empleado administrativo",
            "GERENTE": "Gerente",
            "JEFE": "Jefe de área",
            "SECRETARIA": "Secretaria",
            "SUB GERENTE": "Sub gerente",
            "GERENTE CORPORATIVO": "Gerente corporativo",
            "PRACTICANTE": "Excluido automáticamente por filtro de seguridad"
        }
    },
    # Agrupación FFVV vs ADMIN (Dimensión Calculada)
    "grupo_segmento": {
        "sql": """
            CASE 
                WHEN segmento = 'EMPLEADO FFVV' THEN 'Fuerza de Ventas'
                WHEN segmento = 'PRACTICANTE' THEN 'Practicante'
                ELSE 'Administrativo'
            END
        """,
        "category": "segmentation",
        "label": "Grupo de Segmento",
        "description": "Agrupación binaria: Fuerza de Ventas (solo EMPLEADO FFVV) vs Administrativo (todos los demás excepto PRACTICANTE)",
        "value_definitions": {
            "Fuerza de Ventas": "EMPLEADO FFVV únicamente",
            "Administrativo": "EMPLEADO, GERENTE, JEFE, SECRETARIA, SUB GERENTE, JUR GERENTE, GERENTE CORPORATIVO, etc.",
            "Practicante": "Excluido automáticamente por filtro de seguridad"
        }
    },
    
    # Talent Classification (Calculated)
    "grupo_talento": {
        "sql": """
            CASE 
                WHEN mapeo_talento_ultimo_anio = 7 THEN 'HiPer'
                WHEN mapeo_talento_ultimo_anio IN (8, 9) THEN 'HiPo'
                ELSE 'Regular'
            END
        """,
        "category": "segmentation",
        "label": "Grupo Talento (HiPer/HiPo)",
        "description": "Clasificación de Talento Clave: HiPer (Alto Desempeño), HiPo (Potenciales).",
        "value_definitions": {
            "HiPer": "High Performer (Valor 7)",
            "HiPo": "High Potential (Potenciales - Valores 8, 9)",
            "Regular": "Otros valores"
        }
    },
    # Fix for WHERE clauses: Explicitly use the RAW SQL expression, not the alias 'grupo_talento'
    "talento": {
        "sql": """
            CASE 
                WHEN mapeo_talento_ultimo_anio = 7 THEN 'HiPer'
                WHEN mapeo_talento_ultimo_anio IN (8, 9) THEN 'HiPo'
                ELSE 'Regular'
            END
        """, 
        "category": "segmentation", 
        "label": "Talento (Grupo)"
    },
    "mapeo_talento": {"sql": "mapeo_talento_ultimo_anio", "category": "segmentation", "label": "Mapeo Talento (Raw)"},
    "mapeo_talento_ultimo_anio": {"sql": "mapeo_talento_ultimo_anio", "category": "segmentation", "label": "Mapeo Talento (Raw)"},

    "motivo": {"sql": "motivo_cese", "category": "segmentation", "label": "Motivo de Cese"},
    "motivo_cese": {
        "sql": "motivo_cese", 
        "category": "segmentation", 
        "label": "Motivo de Cese (Legal)",
        "description": "Categoría legal (Macro). Valores: ABANDONO DE TRABAJO, DESPIDO O DESTITUCIÓN, FALLECIMIENTO, FALTA GRAVE, MUTUO DISENSO, PERIODO DE PRUEBA, RENUNCIA, RETIRO DE CONFIANZA, TÉRMINO DE CONTRATO."
    },
    "tipo_contrato": {"sql": "tipo_contrato", "category": "segmentation", "label": "Tipo Contrato"},
    "jerarquia": {"sql": "jerarquia_ffvv", "category": "segmentation", "label": "Jerarquía FFVV"},
    "rango_permanencia": {"sql": "rango_permanencia", "category": "segmentation", "label": "Rango Permanencia"},
    "rango_anio": {"sql": "rango_anio", "category": "segmentation", "label": "Rango Año"},
    
    # Estado (CRÍTICO para filtros de rotación vs activos)
    "estado": {"sql": "estado", "category": "segmentation", "label": "Estado"},
    
    # Financial / Performance (PER = Penetration Rate)
    # Dato pre-calculado en origen: % penetración vs banda mercado.
    # Dato pre-calculado en origen: % penetración vs banda mercado.
    "per_anual": {
        "sql": "per_anual", 
        "category": "financial", 
        "label": "PER Anual (%)",
        "type": "ratio"
    },
    "percentil": {"sql": "percentil", "category": "financial", "label": "Percentil"},
    "salario": {"sql": "salario_mensual", "category": "segmentation", "label": "Salario Mensual"},
    
    # Talent / Profile
    "ggs": {"sql": "ggs", "category": "organizational", "label": "GGS", "description": "Global Grade System (Nivel jerárquico)"},
    "antiguedad": {"sql": "antiguedad_anos", "category": "organizational", "label": "Antigüedad (Años)"},
    "antiguedad_anos": {"sql": "antiguedad_anos", "category": "organizational", "label": "Antigüedad (Años)"},
    "respuestas": {
        "sql": "respuestas", 
        "category": "other", 
        "label": "Detalle Renuncia (Respuestas)",
        "description": "Motivo específico/causa raíz de la renuncia declarado por el colaborador. Usar cuando piden detalles de por qué renunciaron."
    }
}

# -----------------------------------------------------------------------------
# FILTROS DE SEGURIDAD Y NEGOCIO (WHERE CLAUSES)
# -----------------------------------------------------------------------------
MANDATORY_FILTERS = [
    # Regla de Oro: Excluir practicantes
    "segmento != 'PRACTICANTE'",
]

# -----------------------------------------------------------------------------
# DEFAULT FILTERS (BUSINESS RULES)
# -----------------------------------------------------------------------------
# Reglas por defecto según Intent. 
# condition_missing: Solo se aplica si la dimensión NO está ya en los filtros del usuario.
DEFAULT_FILTERS = {
    "LISTING": [
        {
            "dimension": "estado", 
            "value": "Cesado", 
            "condition_missing": ["estado", "status", "situacion"]
        }
    ]
}

# -----------------------------------------------------------------------------
# DEFAULT COLUMNS FOR LISTINGS (SINGLE SOURCE OF TRUTH)
# -----------------------------------------------------------------------------
DEFAULT_LISTING_COLUMNS = [
    "periodo", 
    "uo2", 
    "uo3", 
    "nombre_completo", 
    "posicion", 
    "segmento", 
    "talento", 
    "per_anual", 
    "motivo_cese",
    "fecha_cese"
]
