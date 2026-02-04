# Scripts de Utilidad

Colección de scripts de mantenimiento, depuración y análisis para el backend.

## Scripts Principales

### `analyze_perf.py`
Analizador de logs de rendimiento. Lee el archivo local `.agent/logs/performance.jsonl` (generado por `app/core/utils/perf_logger.py`) y muestra estadísticas en consola.
*   **Uso:** `python scripts/analyze_perf.py [--limit 100]`
*   **Output:** Tabla con Count, Avg, Max y P95 de latencia por herramienta.

### `reset_memory.py`
Herramienta de limpieza profunda de sesiones.
*   **Función:** Se conecta al backend (localhost:8080), se autentica como Admin y purga sesiones de Firestore.
*   **Uso:** `python scripts/reset_memory.py`
*   **Sesiones Target:** Limpia IDs comunes de desarrollo (`session-admin`, `default`, etc.).

## Utils (`scripts/utils/`)

### `force_gc.py`
Snippet simple para invocar el Garbage Collector de Python. Útil en entornos con memoria limitada (Cloud Run) si se detectan fugas.
