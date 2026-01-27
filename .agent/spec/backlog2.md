### BACKLOG DE TOOLS: CAPACIDADES DEL AGENTE DE HR ANALYTICS

#### 1. TOOL: get_turnover_deep_dive
* **Descripción Humana:** Permite realizar un desglose quirúrgico de la rotación. El usuario puede preguntar "¿Cómo va la rotación en la División de Tecnología a nivel de Jefaturas?" y el sistema cruzará las Unidades Organizacionales (UO2 a UO6) con los segmentos.
* **Alcance:**
    * [cite_start]Cálculo de Rotación General y Voluntaria (Renuncias)[cite: 1258].
    * Análisis por cualquier nivel de jerarquía flexible (UO2-UO6).
    * [cite_start]Exclusión automática de Practicantes para KPIs oficiales de Negocio[cite: 1258].
* **Parámetros Técnicos:**
    * `dimension`: (String) Columna de agrupación (ej. 'uo2', 'segmento', 'posicion').
    * `periodo_inicio` / `periodo_fin`: (Date) Rango de análisis.
    * `tipo_rotacion`: (Enum) ['GENERAL', 'VOLUNTARIA'].
* **Lógica de Negocio (SQL):** * Numerador: `COUNT(dni)` donde `estado = 'Cesado'`. [cite_start]Si es 'VOLUNTARIA', añadir `motivo_cese = 'RENUNCIA'`[cite: 117, 1258].
    * [cite_start]Denominador: `HC_INICIAL` (Activos al cierre del mes anterior)[cite: 1258].

#### 2. TOOL: get_talent_leakage (Fuga de Talento Crítico)
* **Descripción Humana:** Identifica la pérdida de colaboradores con alto potencial. Responde a preguntas sobre los cortes específicos de la matriz de talento.
* **Cortes Específicos:**
    * [cite_start]**TALENTO (7, 8 y 9):** Incluye Hipers (7) e Hipos (8 y 9)[cite: 715, 718].
    * [cite_start]**HIPOS (8 y 9):** Solo el segmento de High Potentials[cite: 720, 796].
* **Alcance:**
    * [cite_start]Reporte de `N° Ceses` y `% Rotación Anualizada` para estos grupos[cite: 775, 788].
    * Identificación de "Quiénes" se están yendo (Lista de nombres y posiciones).
* **Parámetros Técnicos:**
    * `segmento_talento`: (Enum) ['TALENTO_TOTAL', 'HIPOS_ONLY'].
    * `periodo`: (Date) Mes o año en evaluación.
* **Lógica de Negocio (SQL):**
    * Si `TALENTO_TOTAL`: Filtro `mapeo_talento_ultimo_anio IN (7, 8, 9)`.
    * Si `HIPOS_ONLY`: Filtro `mapeo_talento_ultimo_anio IN (8, 9)`.

#### 3. TOOL: predict_attrition_factors (Análisis de Correlación)
* **Descripción Humana:** Herramienta de diagnóstico para encontrar patrones de fuga. ¿La gente se va por el supervisor? ¿Por el tiempo de servicio? ¿Por la sede? 
* **Alcance:**
    * [cite_start]Correlación entre `motivo_cese` y `supervisor`[cite: 1, 1010].
    * [cite_start]Análisis de "Supervivencia": Relación entre `ts_anios` (Tenencia) y la probabilidad de cese[cite: 1, 171].
    * [cite_start]Desglose por `sub_motivo_cese` (ej. Oportunidad laboral, Liderazgo, Clima)[cite: 997, 1017].
* **Parámetros Técnicos:**
    * `factor_analisis`: (Enum) ['SUPERVISOR', 'TENENCIA', 'SEDE', 'MOTIVO'].
    * `uo2_filter`: (Optional) Filtrar por División.
* **Lógica de Negocio (SQL):** * Ranking de supervisores con mayor tasa de ceses voluntarios.
    * [cite_start]Agrupación por `rango_permanencia` para identificar el "valle de fuga" (ej. ¿se van todos a los 2 años?)[cite: 1, 21].

---
**Reglas de Oro para el Agente (System Prompt):**
1. [cite_start]Siempre que se hable de "Ventas" o "FFVV", aplicar el filtro `segmento = 'EMPLEADO FFVV'`[cite: 195].
2. [cite_start]La rotación de "HIPERS (7)" siempre debe compararse contra el total de "TALENTO (7, 8 y 9)" para dar contexto de criticidad[cite: 846, 847].
3. Si el dato de `uoX` no tiene nombre de área (está vacío), reportarlo como "No Definido en Estructura" para alertar limpieza de datos.