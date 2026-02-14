
# Registro central de Verdades de Negocio (Semantic Layer)
# Este archivo define QUÉ medida es válida y CÓMO se calcula.

# -----------------------------------------------------------------------------
# DICCIONARIO DE MÉTRICAS (METRICS STORE)
# -----------------------------------------------------------------------------
METRICS_REGISTRY = {
    # DEPRECATED: Use get_headcount_metrics tool for all Rotation Rates to ensure Headcount Avg logic.
    # "tasa_rotacion": {
    #     "sql": "SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN estado = 'Cesado' THEN codigo_persona END), COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END)) * 100",
    #     "label": "Tasa de Rotación Global (%)",
    #     "description": "Porcentaje de salidas respecto al total de activos en el periodo.",
    #     "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},
    #     "type": "ratio"
    # },
    # "tasa_rotacion_voluntaria": {
    #     "sql": "SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) LIKE '%renuncia%' THEN codigo_persona END), COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END)) * 100",
    #     "label": "Tasa de Rotación Voluntaria (%)",
    #     "description": "Porcentaje de renuncias respecto al total de activos.",
    #     "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},
    #     "type": "ratio"
    # },
    # "tasa_rotacion_involuntaria": {
    #     "sql": "SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) NOT LIKE '%renuncia%' THEN codigo_persona END), COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END)) * 100",
    #     "label": "Tasa de Rotación Involuntaria (%)",
    #     "description": "Porcentaje de despidos/bajas respecto al total de activos.",
    #     "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},
    #     "type": "ratio"
    # },
    "personal_activo_total": {
        "sql": "COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END)",
        "label": "Personal Activo Total",
        "description": "Cantidad total de personas únicas activas en el periodo.",
        "agent_instruction": "AGENTE: USAR ESTA MÉTRICA PARA 'TOTAL HEADCOUNT', 'TOTAL EMPLEADOS' O 'PERSONAL TOTAL'. Cuenta personas únicas activas en el periodo. NO USAR PROMEDIOS.",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "count",
        "complexity": "simple"
    },
    "ceses_totales": {
        "sql": "COUNT(DISTINCT CASE WHEN estado = 'Cesado' THEN codigo_persona END)",
        "label": "Personal Cesado Total",
        "description": "Total de bajas en el periodo. Fórmula: COUNT(DISTINCT codigo_persona) WHERE estado='Cesado'.",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "count",
        "complexity": "simple"  # Agregación directa
    },
    "ceses_voluntarios": {
        "sql": "COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) LIKE '%renuncia%' THEN codigo_persona END)",
        "label": "Personal Cesado Voluntario Total",
        "description": "Total de renuncias. Fórmula: COUNT WHERE estado='Cesado' AND motivo LIKE '%renuncia%'.",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "count",
        "complexity": "simple"  # Agregación directa
    },
    "ceses_involuntarios": {
        "sql": "COUNT(DISTINCT CASE WHEN estado = 'Cesado' AND LOWER(motivo_cese) NOT LIKE '%renuncia%' THEN codigo_persona END)",
        "label": "Ceses Involuntarios",
        "description": "Cantidad absoluta de personas desvinculadas.",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "count",
        "complexity": "simple"  # Agregación directa
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
    
    # =========================================================================
    # MÉTRICAS COMPLEJAS (Requieren CTEs + Window Functions)
    # =========================================================================
    # Estas métricas no pueden calcularse con un simple SELECT + GROUP BY.
    # Requieren Common Table Expressions (CTEs) con LAG, AVG OVER, etc.
    # El query_generator detectará estas métricas y generará SQL especializado.
    
    "headcount_inicial": {
        "sql": "hc_inicial",  # Referencia a columna calculada en CTE
        "label": "HC Inicial (Mes)",
        "description": "Headcount al inicio del mes (HC Final del mes anterior via LAG).",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "calculated",
        "requires_cte": "headcount_base"  # Indica que necesita el CTE headcount_base
    },
    "headcount_final": {
        "sql": "hc_final",
        "label": "HC Final (Cierre Mes)",
        "description": "Headcount al cierre del mes (Activos al final del periodo).",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "calculated",
        "requires_cte": "headcount_base"
    },
    "headcount_promedio_mensual": {
        "sql": "headcount_promedio_mensual",
        "label": "HC Promedio Mensual (Legacy)",
        "description": "Promedio mensual: (HC Inicial + HC Final) / 2.",
        "agent_instruction": "AGENTE: ⚠️ NOTA: Esta métrica NO se usa para cálculo de tasas de rotación. Para rotación se usa HC Final del mes anterior (hc_inicial).",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "calculated",
        "requires_cte": "headcount_base"
    },
    "headcount_promedio_acumulado": {
        "sql": "hc_promedio_acumulado",
        "label": "HC Promedio YTD",
        "description": "Promedio acumulado de cierres mensuales.",
        "agent_instruction": "AGENTE: USAR SOLO SI EL USUARIO PIDE EXPLICITAMENTE 'PROMEDIO'. NO USAR PARA 'TOTAL HEADCOUNT'. Promedio acumulado de cierres mensuales.",
        "format": {"unit_type": "count", "symbol": None, "decimals": 0},
        "type": "calculated",
        "requires_cte": "headcount_base"
    },
    "tasa_rotacion_mensual": {
        "sql": "tasa_rotacion_mensual",
        "label": "Tasa Rotación Mensual (%)",
        "description": "Fórmula: (Ceses del Mes / HC Final del Mes Anterior) * 100. Usa HC Inicial (LAG de HC Final).",
        "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},
        "type": "calculated",
        "requires_cte": "headcount_base",
        "informative_metrics": ["ceses_totales", "headcount_inicial"]
    },
    "tasa_rotacion_mensual_voluntaria": {
        "sql": "tasa_rotacion_mensual_voluntaria",
        "label": "Tasa Rotación Voluntaria Mensual (%)",
        "description": "Tasa de Renuncia. Fórmula: (Ceses Voluntarios del Mes / HC Final del Mes Anterior) * 100.",
        "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},
        "type": "calculated",
        "requires_cte": "headcount_base",
        "informative_metrics": ["ceses_voluntarios", "headcount_inicial"]
    },
    "tasa_rotacion_mensual_involuntaria": {
        "sql": "tasa_rotacion_mensual_involuntaria",
        "label": "Tasa Rotación Involuntaria Mensual (%)",
        "description": "Fórmula: (Ceses Involuntarios del Mes / HC Final del Mes Anterior) * 100.",
        "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},
        "type": "calculated",
        "requires_cte": "headcount_base",
        "informative_metrics": ["ceses_involuntarios", "headcount_inicial"]
    },
    "tasa_rotacion_anual": {
        "sql": "tasa_rotacion_anual",
        "label": "Tasa Rotación Anual YTD (%)",
        "description": "Fórmula: (Ceses Totales del Año / HC Promedio Anual) * 100. HC Promedio = (SUM HC Finales / n_meses).",
        "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},
        "type": "calculated",
        "requires_cte": "headcount_base",
        "informative_metrics": ["ceses_totales", "headcount_promedio_acumulado"]
    },
    "tasa_rotacion_anual_voluntaria": {
        "sql": "tasa_rotacion_anual_voluntaria",
        "label": "Tasa Rotación Voluntaria Anual YTD (%)",
        "description": "Tasa de Renuncia Acumulada. Fórmula: (Ceses Voluntarios Totales / HC Promedio Anual) * 100.",
        "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},

        "type": "calculated",
        "requires_cte": "headcount_base",
        "informative_metrics": ["ceses_voluntarios", "headcount_promedio_acumulado"]
    },
    "tasa_rotacion_anual_involuntaria": {
        "sql": "tasa_rotacion_anual_involuntaria",
        "label": "Tasa Rotación Involuntaria Anual YTD (%)",
        "description": "Fórmula: (Ceses Involuntarios Totales / HC Promedio Anual) * 100.",
        "format": {"unit_type": "percentage", "symbol": "%", "decimals": 2},
        "type": "calculated",
        "requires_cte": "headcount_base",
        "informative_metrics": ["ceses_involuntarios", "headcount_promedio_acumulado"]
    }
    # "headcount_promedio": {
    #     "sql": """
    #     (
    #          (
    #             SELECT COUNT(DISTINCT codigo_persona) 
    #             FROM {TABLE} 
    #             WHERE fecha_corte = DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 MONTH)
    #             AND estado = 'Activo'
    #          ) +
    #          COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END)
    #     ) / 2
    #     """,
    #     "label": "Headcount Promedio (Legacy)",
    #     "description": "Promedio simple (Inicial + Final) / 2.",
    #     "format": {"unit_type": "count", "symbol": None, "decimals": 0},
    #     "type": "avg"
    # }

}

# -----------------------------------------------------------------------------
# DICCIONARIO DE DIMENSIONES Y FILTROS
# -----------------------------------------------------------------------------
DIMENSIONS_REGISTRY = {
    # Organizacionales
    "uo2": {"sql": "uo2", "category": "organizational", "label": "División"},
    "division": {"sql": "uo2", "category": "organizational", "label": "División"}, # Alias
    "uo3": {
        "sql": "uo3", 
        "category": "organizational", 
        "label": "Tipo de Canal (UO3)",
        "description": "Nivel Macro del Canal: 'CANALES DIRECTOS', 'CANALES INDIRECTOS', 'VENTAS', etc.",
        "value_definitions": {
            "CANALES DIRECTOS": "Canales Directos",
            "CANALES INDIRECTOS": "Canales Indirectos",
            "VENTAS": "Ventas (General)",
            "TRIBU VIDA": "Tribu Vida",
            "TRIBU P&C": "Tribu P&C"
        }
    },
    "tipo_canal": {"sql": "uo3", "category": "organizational", "label": "Tipo Canal"}, # Alias
    "canal_macro": {"sql": "uo3", "category": "organizational", "label": "Canal Macro"}, # Alias

    "uo4": {
        "sql": "uo4", 
        "category": "organizational", 
        "label": "Canal (Detalle/Raw) / UO4",
        "description": "Nivel previo de canal desagregado. NO USAR como dimensión principal de canal (usar 'uo5').",
        "value_definitions": {
            "FFVV MULTIPRODUCTO": "FFVV Multiproducto (Raw)",
            "FFVV CONVENIOS": "FFVV Convenios (Raw)"
        }
    },
    "canal_raw": {"sql": "uo4", "category": "organizational", "label": "Canal (Raw)"}, 
    
    "uo5": {
        "sql": "uo5",
        "category": "organizational",
        "label": "Canal (Homologado) / UO5",
        "description": "Canal de Venta Principal y Homologado.",
        "value_definitions": {
            "FFVV MULTIPRODUCTO": "Fuerza de Ventas Vida (Multiproducto)",
            "FFVV CONVENIOS": "Fuerza de Ventas Convenios",
            "FFVV VIDA": "Fuerza de Ventas Vida (General)",
            "FFVV RENTAS": "Fuerza de Ventas Rentas",
            "FFVV PROSPEROUS": "Fuerza de Ventas Prosperous",
            "CANAL VIP": "Canal VIP",
            "BANCASEGUROS Y ALIANZAS": "Bancaseguros",
            "CORREDORES": "Corredores",
            "TIENDA RIMAC": "Tienda Rimac",
            "VEHICULOS": "Vehículos"
        }
    },
    "canal": {"sql": "uo5", "category": "organizational", "label": "Canal"}, # Alias Principal para 'Canal' (AHORA UO5)
    "canal_detalle": {"sql": "uo5", "category": "organizational", "label": "Canal (Detalle)"}, # Alias también a UO5
    "posicion": {
        "sql": "posicion", 
        "category": "organizational", 
        "label": "Posición",
        "force_upper": True,
        "value_groups": {
            "GERENTES DE OFICINA": ["GERENTE DE AGENCIA", "GERENTE DE OFICINA", "GERENTE DE OFICINA VIP"],
            "LIDERES COMERCIALES": ["JEFE DE VENTAS", "SUPERVISOR", "GERENTE REGIONAL"]
        }
    },
    "cargo": {"sql": "posicion", "category": "organizational", "label": "Cargo"}, # Alias para posicion
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
    "genero": {"sql": "sexo", "category": "personal", "label": "Género"}, # Alias para sexo
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
    "trimestre": {
        "sql": "EXTRACT(QUARTER FROM periodo)", 
        "category": "temporal", 
        "label": "Trimestre",
        "type": "integer",
        "sorting": "numeric",
        "description": "Trimestre del año (1-4). Usar con 'anio' para filtrar periodos específicos."
    },
    "q": {"sql": "EXTRACT(QUARTER FROM periodo)", "category": "temporal", "label": "Trimestre (Alias)"},
    "grupo_periodo": {
        "sql": "CONCAT(CAST(EXTRACT(YEAR FROM periodo) AS STRING), 'Q', CAST(EXTRACT(QUARTER FROM periodo) AS STRING))", 
        "category": "temporal", 
        "label": "Periodo Trimestral (Formato)",
        "description": "Formato 'YYYYQ#' (Ej: 2025Q1). SOLO para visualización en SELECT, NO usar en filtros WHERE."
    },
    "periodo": {
        "sql": "periodo",  # Ya es STRING en formato YYYYMM en BigQuery
        "category": "temporal",
        "label": "Periodo (YYYYMM)",
        "type": "temporal",
        "description": "Formato YYYYMM (Ej: 202501). Usar para filtrar por mes específico."
    },
    "fecha_ingreso": {"sql": "fecha_ingreso", "category": "temporal", "label": "Fecha Ingreso"},
    "fecha_cese": {"sql": "fecha_cese", "category": "temporal", "label": "Fecha Cese"},
    "anio_ingreso": {
        "sql": "anio_ingreso",
        "category": "temporal",
        "label": "Año de Ingreso",
        "type": "temporal",
        "sorting": "numeric"
    },

    # Talento y Performance
    "mapeo_talento_ultimo_anio": {
        "sql": "mapeo_talento_ultimo_anio",
        "category": "performance",
        "label": "Mapeo Talento",
        "type": "integer",
        "description": "Clasificación de talento del colaborador"
    },
    "per_anual": {
        "sql": "per_anual",
        "category": "performance",
        "label": "Performance Anual",
        "description": "Evaluación de performance anual del colaborador"
    },
    "ggs": {
        "sql": "ggs",
        "category": "performance",
        "label": "GGS",
        "description": "Grid de Gestión de Sucesión"
    },
    "percentil": {
        "sql": "percentil",
        "category": "performance",
        "label": "Percentil",
        "description": "Percentil de performance del colaborador"
    },

    # Permanencia y Antigüedad
    "ts_anios": {
        "sql": "ts_anios",
        "category": "tenure",
        "label": "Antigüedad (Años)",
        "type": "float",
        "description": "Tiempo de servicio en años"
    },
    "ts_dias": {
        "sql": "ts_dias",
        "category": "tenure",
        "label": "Antigüedad (Días)",
        "type": "float",
        "description": "Tiempo de servicio en días"
    },
    "rango_permanencia": {
        "sql": "rango_permanencia",
        "category": "tenure",
        "label": "Rango Permanencia",
        "description": "Rango de antigüedad del colaborador (ej: 0-1 años, 1-3 años, etc.)"
    },

    # FFVV Específico
    "jerarquia_ffvv": {
        "sql": "jerarquia_ffvv",
        "category": "organizational",
        "label": "Jerarquía FFVV",
        "description": "Jerarquía específica para Fuerza de Ventas"
    },

    # Exit Interview / Motivos
    "respuestas": {
        "sql": "respuestas",
        "category": "exit_interview",
        "label": "Motivo Principal Renuncia",
        "description": "Datos categóricos del motivo principal de renuncia (exit interview)"
    },
    "mes_anio_ingreso": {"sql": "mes_anio_ingreso", "category": "temporal", "label": "Mes/Año Ingreso"},

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
