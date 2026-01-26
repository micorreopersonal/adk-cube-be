# HU-001: Análisis de Rotación Mensual (Técnico)

## 1. Arquitectura de Solución
*   **Agente:** `hr_agent` (Google ADK).
*   **Herramienta Principal:** `get_monthly_attrition` en `app/tools/bq_queries/hr_metrics.py`.
*   **Fuente de Datos:** Tabla BigQuery `attrition_table`.

## 2. Diseño de la Query (Lógica SQL)
```sql
WITH HC_Inicial AS (
    SELECT COUNT(*) as hc
    FROM `project.dataset.attrition_table`
    WHERE fecha_corte = DATE_SUB(DATE('{year}-{month}-01'), INTERVAL 1 MONTH)
    AND segmento != 'PRACTICANTE'
),
Cesados AS (
    SELECT 
        COUNT(*) as total,
        COUNTIF(LOWER(motivo_cese) LIKE '%renuncia%') as voluntario
    FROM `project.dataset.attrition_table`
    WHERE EXTRACT(MONTH FROM fecha_cese) = {month}
    AND EXTRACT(YEAR FROM fecha_cese) = {year}
    AND segmento != 'PRACTICANTE'
)
SELECT 
    total as cesados_totales,
    voluntario as cesados_voluntarios,
    SAFE_DIVIDE(total, hc) as tasa_general,
    SAFE_DIVIDE(voluntario, hc) as tasa_voluntaria
FROM HC_Inicial, Cesados
```

## 3. Orquestación
El `hr_agent` utilizará el `Runner` de ADK para mantener el estado de la conversación. No se requieren sub-agentes para esta HU, ya que todas las métricas residen en la misma fuente de datos y comparten el mismo contexto de seguridad.
