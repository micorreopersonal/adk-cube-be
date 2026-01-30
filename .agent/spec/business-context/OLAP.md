# ==============================================================================
# PRODUCT BACKLOG: HR ANALYTICS AGENT - RETENTION & TURNOVER TOOLS
# ==============================================================================
# Proyecto: IA Agent para Análisis de Rotación Multidimensional
# Estado: Refinado (Ready for Development)
# Lógica de Denominador: Headcount Promedio (HC_Avg)
# ==============================================================================

"""
TOOL 1: get_turnover_stats
--------------------------------------------------------------------------------
OBJETIVO: Calcular métricas base de rotación para periodos específicos o rangos.
INPUTS:
    - periods: List[Date] -> Lista de meses a incluir (ej. ['2025-01-01', '2025-03-01'])
    - filters: Dict -> Filtros opcionales (ej. {'segmento': 'EMPLEADO', 'uo2': 'DIV SEGUROS'})

LÓGICA SQL (Pseudocódigo para BQ):
    1. Numerador (Ceses):
       COUNT(DISTINCT codigo_persona) WHERE estado = 'Cesado' AND periodo IN UNNEST(periods)
    2. Numerador Voluntario:
       COUNT(DISTINCT codigo_persona) WHERE estado = 'Cesado' AND motivo_cese = 'RENUNCIA' AND periodo IN UNNEST(periods)
    3. Denominador (HC Promedio):
       AVG(
         SELECT COUNT(DISTINCT codigo_persona) 
         FROM tabla WHERE estado = 'Activo' AND periodo IN UNNEST(periods)
         GROUP BY periodo
       )
    4. Métricas:
       - Turnover_Rate = (Total_Ceses / HC_Promedio)
       - Voluntary_Turnover_Rate = (Ceses_Voluntarios / HC_Promedio)
"""

"""
TOOL 2: get_multidimensional_breakdown
--------------------------------------------------------------------------------
OBJETIVO: Realizar el "Corte" o Drill-down de datos por dimensiones dinámicas.
INPUTS:
    - periods: List[Date]
    - group_by_columns: List[String] -> Dimensiones de la tabla (ej. ['uo4', 'segmento'])
    - filters: Dict -> Filtros aplicados al sub-universo.

LÓGICA DE NEGOCIO:
    1. Manejo de Nulos: Aplicar COALESCE(columna, 'N/A') a todas las dimensiones en group_by.
    2. Agregación: Calcular Ceses y HC Promedio para cada combinación única de las columnas en group_by.
    3. Retorno: Tabla con [Dimensión 1, Dimensión 2, ..., HC_Promedio, Total_Ceses, %_Rotacion].
"""

"""
TOOL 3: get_turnover_trend
--------------------------------------------------------------------------------
OBJETIVO: Analizar la tendencia temporal (Time-Series) para detectar estacionalidad.
INPUTS:
    - start_period: Date
    - end_period: Date
    - dimension: String (opcional para comparar líneas de tendencia)

LÓGICA:
    - Retorna el % de rotación mes a mes en el rango seleccionado.
"""

# ==============================================================================
# REGLAS DE NEGOCIO ADICIONALES (PARA EL AGENTE)
# ==============================================================================
# 1. TRATAMIENTO DE N/A: El Agente debe mostrar 'N/A' en los resultados pero añadir un disclaimer: "Se incluyen registros no asignados a una estructura específica".
# 2. JERARQUÍA DE DIMENSIONES: El Agente debe priorizar el orden de agrupamiento según el pedido del usuario (Ej: "Corta por UO4 y luego por Segmento").
# 3. FILTRO DE PRACTICANTES: Por política de HR, excluir 'P. PRE-PROFESIONAL' y 'P. PROFESIONAL' de la rotación general a menos que se solicite explícitamente.
# 4. CÁLCULO VOLUNTARIO: Siempre reportar la rotación voluntaria como un subset de la rotación total para identificar problemas de clima laboral.