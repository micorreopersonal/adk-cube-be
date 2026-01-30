# Especificación Técnica (HU-008)

## Modificación de `app/ai/tools/bq_queries/leavers.py`

### 1. Actualización de Firma
```python
def get_leavers_distribution(
    periodo: str, 
    breakdown_by: str = "division",
    tipo_rotacion: str = "VOLUNTARIA", 
    segmento: str = "TOTAL",
    tipo_talento: Optional[str] = None # NUEVO
) -> Dict[str, Any]:
```

### 2. Mapeo de Filtros de Talento
*   `HIPERS` -> `(7)`
*   `HIPOS` -> `(8, 9)`
*   `TODO_TALENTO` -> `(7, 8, 9)`

### 3. Lógica SQL
```sql
-- Si tipo_talento existe
AND mapeo_talento_ultimo_anio IN {talento_tuple}
```

### 4. Mejora de Título Dinámico
El título del gráfico debe reflejar si tiene filtro de talento (ej. "Distribución de Talento Clave por División").

## Robustez Global
Para evitar futuros 500s por parámetros extra, se agregará `**kwargs` a todas las tools del agente o se capturará el error en `AgentRouter`.
**Decisión:** Agregar `**kwargs` a las tools es la forma más limpia de "degradar" silenciosamente parámetros alucinados sin romper el flujo.
