# HU-008: Filtrado de Talento en Análisis Distributivo

## 1. El Problema
El usuario desea ver distribuciones (ej. "por División") pero solo de un grupo específico: **Talento Clave (Hipos/Hipers)**.
Actualmente:
*   `get_talent_alerts` lista personas pero no agrupa.
*   `get_leavers_distribution` agrupa pero no tiene filtro de talento.
*   **Consecuencia:** El LLM intenta "inventar" el parámetro, lo que causa un `TypeError` y un **Error 500** en el backend.

## 2. La Solución
Extender `get_leavers_distribution` para soportar un filtro de talento opcional.

### Cambios Propuestos:
1.  **Backend (`leavers.py`):**
    *   Nuevo parámetro: `tipo_talento` (str, opcional). Valores: `HIPERS`, `HIPOS`, `TODO_TALENTO`.
    *   Lógica SQL: Agregar `AND mapeo_talento_ultimo_anio IN (...)` al query.

2.  **Agente (Prompt):**
    *   Actualizar descripción de la tool para que el LLM sepa que puede filtrar por talento en los gráficos.

## 3. Valor para el Negocio
Permite responder preguntas críticas de BI como: "¿En qué divisiones estamos perdiendo más talento Hiper/Hipo?".
Elimina errores técnicos por falta de capacidad de cruce de datos.
