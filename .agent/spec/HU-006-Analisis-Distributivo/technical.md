# Especificación Técnica (HU-006)

## Nueva Tool: `get_leavers_distribution`
Archivo: `app/ai/tools/bq_queries/leavers.py` (Se extenderá este archivo o se creará `distribution.py`).

### Firma de la Función
```python
def get_leavers_distribution(
    periodo: str,
    breakdown_by: str,  # "UO2", "UO3", "MOTIVO", "POSICION"
    dimension: Optional[str] = None, # Filtro opcional previo
    segmento: str = "TOTAL"
) -> Dict[str, Any]:
```

### Lógica SQL
Dinámica según `breakdown_by`.
```sql
SELECT 
    {columna_sql} as category,
    COUNT(*) as count
FROM `fact_hr_rotation`
WHERE ... (Mismos filtros de fecha/segmento) ...
GROUP BY 1
ORDER BY 2 DESC
LIMIT 20 -- Top 20 para evitar ruido visual
```
*Mapeo de columnas:*
*   "UO2" -> `uo2`
*   "UO3" -> `uo3`
*   "MOTIVO" -> `motivo_cese`
*   "POSICION" -> `posicion`

### ResponseBuilder Integration
Se añadirá un método `add_distribution_chart(data, type='bar')` al `ResponseBuilder` (`app/ai/utils/response_builder.py`).
Este método formateará la salida para que el Frontend (Streamlit/React) sepa renderizarla.

### Manejo de Cardinalidad
Para evitar gráficos ilegibles con 50 barras:
1.  El SQL limitará a `Top 15`.
2.  (Futuro) Python sumará el resto en una categoría "OTROS".
