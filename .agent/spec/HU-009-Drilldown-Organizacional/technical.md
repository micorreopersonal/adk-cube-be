# HU-009: Especificación Técnica

## Arquitectura de la Solución
Se reemplazará el código mock de `get_turnover_deep_dive` por una implementación dinámica basada en BigQuery.

### 1. Parámetros de la Tool
- `parent_level`: (str) Nivel actual de análisis (ej. "UO2").
- `parent_value`: (str) Valor del filtro (ej. "DIVISION SALUD").
- `drill_down_to`: (str) Nivel al que se desea profundizar (ej. "UO3").

### 2. Lógica SQL (Engine)
La query utilizará una CTE para el benchmark y un JOIN para el comparativo:
```sql
WITH ParentStats AS (
    SELECT AVG(tasa_rotacion) as benchmark
    FROM turnover_table
    WHERE {parent_level} = '{parent_value}'
),
ChildrenStats AS (
    SELECT {drill_down_to} as sub_unit, tasa_rotacion, conteo_ceses
    FROM turnover_table
    WHERE {parent_level} = '{parent_value}'
)
SELECT sub_unit, tasa_rotacion, benchmark
FROM ChildrenStats, ParentStats
WHERE tasa_rotacion > benchmark
ORDER BY tasa_rotacion DESC
```

### 3. Componentes a Modificar
- `app/ai/tools/bq_queries/turnover.py`: Implementación real de `get_turnover_deep_dive`.
- `app/ai/agents/hr_agent.py`: Actualizar el prompt para que el agente entienda cuándo invocar el drill-down organizacional.

## Consideraciones de Performance
- Uso de `lru_cache` para resultados de benchmarks de divisiones grandes.
- Límitación de 10 sub-unidades en el gráfico para evitar ruido visual.
