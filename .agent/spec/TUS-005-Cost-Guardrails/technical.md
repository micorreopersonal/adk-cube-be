# Especificación Técnica (TUS-005)

## Implementación: BigQuery Client
Archivo: `app/services/bigquery.py`

Se modificará el método `execute_query` para inyectar una configuración de seguridad por defecto:

```python
job_config = bigquery.QueryJobConfig(
    maximum_bytes_billed=10**9,  # 1 GB Limit
    use_query_cache=True
)
query_job = self.client.query(query, job_config=job_config)
```

## Verificación Automática (Dry Run)
Script: `app/ai/evals/test_cost_efficiency.py`

Uso de la API `job.dry_run = True`. Esto permite simular la query sin costo.
**Lógica del Test:**
1.  Tomar una lista de queries representativas del sistema.
2.  Ejecutar Dry Run.
3.  Leer `query_job.total_bytes_processed`.
4.  Assert que `bytes < LIMIT`.
5.  Generar reporte de evidencia.
