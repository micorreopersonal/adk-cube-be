### BACKLOG DE TOOLS: CAPACIDADES DEL AGENTE DE HR ANALYTICS

Este backlog gestiona las capacidades de negocio (Business Capabilities) del Agente.

## 🟢 COMPLETADO (DONE)

### 1. TOOL: get_turnover_deep_dive
* **Descripción Humana:** Permite realizar un desglose quirúrgico de la rotación. El usuario puede preguntar "¿Cómo va la rotación en la División de Tecnología a nivel de Jefaturas?" y el sistema cruzará las Unidades Organizacionales (UO2 a UO6) con los segmentos.
* **Alcance:**
    * Cálculo de Rotación General y Voluntaria (Renuncias).
    * Análisis por cualquier nivel de jerarquía flexible (UO2-UO6).
    * Exclusión automática de Practicantes para KPIs oficiales de Negocio.

### 3. HU-006: Análisis Distributivo y Visualización (Histogramas)
* **Status:** ✅ IMPLEMENTADO
* **Entregable:** Tool `get_leavers_distribution` + `add_distribution_chart`.
* **Evidencia:** `tests/test_hu_006.py` (PASS).

### 3. HU-007: Periodos Flexibles (Zoom Temporal)
* **Status:** ✅ IMPLEMENTADO
* **Entregable:** `get_monthly_trend(month_start, month_end)`.
* **Evidencia:** `tests/test_hu_007.py` (PASS).

### 4. HU-008: Filtro de Talento en Distribuciones
* **Status:** ✅ IMPLEMENTADO
* **Entregable:** Filtro `tipo_talento` en `get_leavers_distribution`.
* **Evidencia:** `tests/test_hu_008.py` (PASS).

### 5. Robustez Global (Anti-Crasheo)
* **Mejora:** Implementación de `**kwargs` en todas las herramientas del Agente.
* **Impacto:** Eliminación de Errores 500 por alucinación de parámetros.

### 6. TOOL: get_turnover_deep_dive
* **Nota:** Implementado como `get_talent_alerts`.
* **Descripción Humana:** Identifica la pérdida de colaboradores con alto potencial. Responde a preguntas sobre los cortes específicos de la matriz de talento.
* **Alcance:**
    * Reporte de `N° Ceses` y `% Rotación Anualizada` para TALENTO (7-9) y HIPOS (8-9).
    * Identificación de "Quiénes" se están yendo (Lista de nombres y posiciones).

---

## 🟡 EN PROGRESO (DOING)
(Sin items activos actualmente)

---

## ⚪ PENDIENTE (TO DO)

### 3. TOOL: predict_attrition_factors (Análisis de Correlación)
* **Descripción Humana:** Herramienta de diagnóstico para encontrar patrones de fuga. ¿La gente se va por el supervisor? ¿Por el tiempo de servicio? ¿Por la sede?
* **Alcance:**
    * Correlación entre `motivo_cese` y `supervisor`.
    * Análisis de "Supervivencia": Relación entre `ts_anios` (Tenencia) y la probabilidad de cese.
    * Desglose por `sub_motivo_cese` (ej. Oportunidad laboral, Liderazgo, Clima).
* **Parámetros Técnicos:**
    * `factor_analisis`: (Enum) ['SUPERVISOR', 'TENENCIA', 'SEDE', 'MOTIVO'].
* **Lógica de Negocio (SQL):**
    * Ranking de supervisores con mayor tasa de ceses voluntarios.
    * Agrupación por `rango_permanencia` para identificar el "valle de fuga".

---
**Reglas de Oro para el Agente (System Prompt):**
1. Siempre que se hable de "Ventas" o "FFVV", aplicar el filtro `segmento = 'EMPLEADO FFVV'`.
2. La rotación de "HIPERS (7)" siempre debe compararse contra el total de "TALENTO (7, 8 y 9)" para dar contexto de criticidad.
3. Si el dato de `uoX` no tiene nombre de área (está vacío), reportarlo como "No Definido en Estructura" para alertar limpieza de datos.