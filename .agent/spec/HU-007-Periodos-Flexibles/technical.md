# Especificación Técnica (HU-007)

## Modificación de `app/ai/tools/bq_queries/hr_metrics.py`

### 1. Refactorización de `get_monthly_trend`
Actualizar la firma de la función:
```python
def get_monthly_trend(
    year: int, 
    segment: Optional[str] = None,
    month_start: int = 1,
    month_end: int = 12
) -> Dict[str, Any]:
```

### 2. Lógica de Filtrado (Post-Processing)
Dado que la query SQL (`_fetch_yearly_series`) está optimizada para traer el año completo en una sola ejecución eficiente, realizaremos el filtrado en Python sobre los vectores resultantes.

**Algoritmo:**
1.  Obtener `series_data` completo (Ene-Dic).
2.  Crear índices de corte basados en `month_start` y `month_end`.
    *   *Nota:* Los arrays vienen ordenados Ene (index 0) -> Dic (index 11).
    *   `idx_start = month_start - 1`
    *   `idx_end = month_end` (para slicing eficiente `[start:end]`).
3.  Recortar todas las listas coordinadas (`months`, `rotacion_general`, `headcount`, etc.).

### 3. Actualización de KPIs Resumen
Los KPIs de "Promedio", "Máximo" y "Mínimo" deben recalcularse usando **solo los datos del rango seleccionado**, para que sean consistentes con lo que ve el usuario.

### 4. Actualización del Agente (`hr_agent.py`)
Actualizar el System Prompt para que el LLM sepa que puede (y debe) extraer rangos de la intención del usuario.
