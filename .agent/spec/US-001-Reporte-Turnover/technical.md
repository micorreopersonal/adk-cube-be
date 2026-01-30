# Especificación Técnica

**Tools:** `get_monthly_attrition`, `get_yearly_attrition`.
**Fuente:** BigQuery `fact_hr_rotation`.
**Filtros:** `segmento != 'PRACTICANTE'`, `estado = 'Activo'` (HC), `estado = 'Cesado'` (Bajas).