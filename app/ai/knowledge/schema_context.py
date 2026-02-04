
"""
Contexto de Conocimiento Semántico para el Agente de SQL Generativo.
Este archivo actúa como la "Fuente de Verdad" para el diseño de queries.
"""

# -----------------------------------------------------------------------------
# 1. DDL DE LA TABLA PRINCIPAL (BigQuery)
# -----------------------------------------------------------------------------
FACT_HR_ROTATION_DDL = """
CREATE TABLE `fact_hr_rotation` (
  codigo_persona STRING,       -- ID único del colaborador (anonimizado)
  nombre_completo STRING,      -- Nombre y Apellido
  posicion STRING,             -- Cargo o puesto actual
  uo2 STRING,                  -- División (Nivel Organizacional 2)
  uo3 STRING,                  -- Área (Nivel Organizacional 3)
  segmento STRING,             -- Segmento de negocio: 'FFVV', 'ADMI', 'PRACTICANTE'
  estado STRING,               -- Estado actual: 'Activo' o 'Cesado'
  fecha_corte DATE,            -- Fecha de corte del registro (snapshot mensual)
  fecha_cese DATE,             -- Fecha efectiva de la baja (solo si estado='Cesado')
  motivo_cese STRING,          -- Razón de la baja (Renuncia, Despido, etc.)
  mapeo_talento_ultimo_anio INT64, -- Calificación de talento: 7=Hiper, 8-9=Hipo
  razon_social STRING,         -- Entidad legal empleadora
  periodo DATE,                -- Primer día del mes del registro (YYYY-MM-01)
  anio INT64                   -- Año numérico (ej: 2025)
);
"""

# -----------------------------------------------------------------------------
# 2. GLOSARIO DE TÉRMINOS Y DIMENSIONES
# -----------------------------------------------------------------------------
DATA_DICTIONARY = {
    "uo2": "División o Unidad de Negocio Principal (ej: 'División Finanzas', 'División Comercial').",
    "uo3": "Área funcional dentro de una División (ej: 'Área de Contabilidad', 'Ventas Zona Norte').",
    "segmento": {
        "FFVV": "Fuerza de Ventas (Personal comercial en campo/tienda).",
        "ADMI": "Administrativos (Personal de oficina/corporativo).",
        "PRACTICANTE": "Estudiantes en prácticas (EXCLUIR siempre de métricas de rotación)."
    },
    "mapeo_talento_ultimo_anio": {
        7: "Hiper (Alto Desempeño Constante - Top Performer). Key Talent.",
        8: "Hipo Nivel 1 (Alto Potencial de Crecimiento). Key Talent.",
        9: "Hipo Nivel 2 (Alto Potencial Temprano). Key Talent.",
        "Otros": "Talento Core/Valued (No considerados críticos para alertas de fuga)."
    },
    "estado": {
        "Activo": "Colaborador trabajando actualmente.",
        "Cesado": "Colaborador que ha dejado la compañía."
    },
    "motivo_cese": {
        "Voluntario": "Contiene 'Renuncia', 'Retiro Voluntario'.",
        "Involuntario": "Despido, Mutuo Disenso, Término de Contrato, Jubilación, Fallecimiento."
    }
}

# -----------------------------------------------------------------------------
# 3. FÓRMULAS DE NEGOCIO (SQL SNIPPETS)
# -----------------------------------------------------------------------------
BUSINESS_FORMULAS = """
-- ============================================================================
-- REGLA DE ORO DE FILTRADO
-- ============================================================================
-- SIEMPRE excluir Practicantes de cualquier cálculo de rotación o HC.
WHERE NOT (LOWER(segmento) LIKE '%practicante%')

-- ============================================================================
-- DEFINICIÓN DE SEGMENTOS PARA COMPARATIVAS (CASE WHEN)
-- ============================================================================
-- Cuando se pida comparar "Fuerza de Ventas" (FFVV) vs "Administrativos":
-- Administrativos NO existe como valor en la columna. Se define por exclusión.
CASE 
    WHEN segmento = 'EMPLEADO FFVV' THEN 'Fuerza de Ventas'
    WHEN segmento NOT IN ('EMPLEADO FFVV', 'PRACTICANTE') THEN 'Administrativos'
    ELSE 'Otros'
END AS segmento_comparativo

-- ============================================================================
-- CÁLCULO DE HEADCOUNT (HC)
-- ============================================================================

-- HC INICIAL (Para un mes específico M)
-- Se toma el stock de Activos al último día del mes ANTERIOR.
HC_INICIAL_MES = (
    SELECT COUNT(DISTINCT codigo_persona)
    FROM `adk-sandbox-486117.data_set_historico_ceses.fact_hr_rotation`
    WHERE fecha_corte = LAST_DAY(DATE_SUB(DATE(año_consulta, mes_consulta, 1), INTERVAL 1 DAY))
    AND estado = 'Activo'
    AND NOT (LOWER(segmento) LIKE '%practicante%')
)

-- HC PROMEDIO (Para métricas anuales o acumuladas)
HC_PROMEDIO = (HC_INICIAL_PERIODO + HC_FINAL_PERIODO) / 2

-- ============================================================================
-- CÁLCULO DE CESES (NUMERADOR)
-- ============================================================================

-- ROTACIÓN TOTAL (Todos los motivos)
TOTAL_CESES = COUNT(DISTINCT codigo_persona)
WHERE estado = 'Cesado'
AND NOT (LOWER(segmento) LIKE '%practicante%')

-- ROTACIÓN VOLUNTARIA (Solo Renuncias)
CESES_VOLUNTARIOS = COUNT(DISTINCT codigo_persona)
WHERE estado = 'Cesado'
AND LOWER(motivo_cese) LIKE '%renuncia%'
AND NOT (LOWER(segmento) LIKE '%practicante%')

-- ROTACIÓN INVOLUNTARIA (Resto)
CESES_INVOLUNTARIOS = Total_Ceses - Ceses_Voluntarios

-- ============================================================================
-- CÁLCULO DE TASAS (RATIOS)
-- ============================================================================

-- TASA MENSUAL DE ROTACIÓN
-- Nota: Usar SAFE_DIVIDE en BigQuery para evitar errores de división por cero.
TASA_MENSUAL = SAFE_DIVIDE(Total_Ceses_Mes, HC_Inicial_Mes) * 100

-- TASA ANUAL DE ROTACIÓN
TASA_ANUAL = SAFE_DIVIDE(Total_Ceses_Año, HC_Promedio_Anual) * 100

-- ============================================================================
-- SEGMENTACIÓN DE TALENTO
-- ============================================================================

-- TALENTO CRÍTICO (Key Talent)
WHERE mapeo_talento_ultimo_anio IN (7, 8, 9)

-- ============================================================================
-- COMPARATIVAS (DELTAS)
-- ============================================================================

-- Delta vs Mes Anterior (MoM)
Delta_MoM = Tasa_Mes_Actual - Tasa_Mes_Anterior

-- Delta vs Promedio del Año (YTD)
Promedio_YTD = AVG(Tasas_De_Enero_a_Mes_Actual)
Delta_vs_Avg = Tasa_Mes_Actual - Promedio_YTD
"""

# -----------------------------------------------------------------------------
# 4. EJEMPLOS DE QUERIES OPTIMIZADAS (Few-Shot Prompting)
# -----------------------------------------------------------------------------
QUERY_EXAMPLES = {
    "tasa_rotacion_mensual_por_division": """
        WITH hc_inicial AS (
            SELECT 
                uo2, 
                COUNT(DISTINCT codigo_persona) as hc
            FROM `adk-sandbox-486117.data_set_historico_ceses.fact_hr_rotation`
            -- HC Inicial es el cierre del mes anterior
            WHERE fecha_corte = DATE_SUB(DATE('2025-11-01'), INTERVAL 1 DAY)
            AND estado = 'Activo'
            AND NOT (LOWER(segmento) LIKE '%practicante%')
            GROUP BY uo2
        ),
        ceses_mes AS (
            SELECT 
                uo2,
                COUNT(DISTINCT codigo_persona) as total_bajas,
                COUNT(DISTINCT IF(LOWER(motivo_cese) LIKE '%renuncia%', codigo_persona, NULL)) as bajas_voluntarias
            FROM `adk-sandbox-486117.data_set_historico_ceses.fact_hr_rotation`
            WHERE EXTRACT(YEAR FROM fecha_cese) = 2025 
            AND EXTRACT(MONTH FROM fecha_cese) = 11
            AND estado = 'Cesado'
            AND NOT (LOWER(segmento) LIKE '%practicante%')
            GROUP BY uo2
        )
        SELECT 
            h.uo2,
            h.hc as headcount_inicial,
            COALESCE(c.total_bajas, 0) as ceses_totales,
            COALESCE(c.bajas_voluntarias, 0) as renuncias,
            SAFE_DIVIDE(COALESCE(c.total_bajas, 0), h.hc) * 100 as tasa_rotacion_total
        FROM hc_inicial h
        LEFT JOIN ceses_mes c ON h.uo2 = c.uo2
        ORDER BY tasa_rotacion_total DESC
    """,
    
    "listado_fugas_talento_critico": """
        SELECT 
            nombre_completo,
            posicion,
            uo2 as division,
            uo3 as area,
            mapeo_talento_ultimo_anio,
            motivo_cese,
            fecha_cese
        FROM `adk-sandbox-486117.data_set_historico_ceses.fact_hr_rotation`
        WHERE estado = 'Cesado'
        -- Filtro de Talento Crítico (7, 8, 9)
        AND mapeo_talento_ultimo_anio IN (7, 8, 9)
        AND EXTRACT(YEAR FROM fecha_cese) = 2025
        AND EXTRACT(MONTH FROM fecha_cese) = 11
        ORDER BY fecha_cese DESC
        LIMIT 100
    """,

    "LISTADO_DETALLADO_CESADOS": """
        -- PATRÓN PARA: "quiénes son", "listar nombres", "detalle de personas", "ceses diciembre"
        SELECT 
            periodo,
            uo2 as division,
            uo3 as area,
            nombre_completo,
            posicion,
            segmento,
            mapeo_talento_ultimo_anio as talento,
            per_anual, -- Dato directo de tabla
            motivo_cese,
            fecha_cese
        FROM `adk-sandbox-486117.data_set_historico_ceses.fact_hr_rotation`
        WHERE uo2 = 'DIVISION SEGUROS PERSONAS' -- O la división solicitada
        AND anio = 2025
        AND mes = 12
        AND estado = 'Cesado'
        ORDER BY fecha_cese DESC
        LIMIT 100
    """
}
