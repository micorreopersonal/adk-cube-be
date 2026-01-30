# 🧠 Bitácora de Aprendizajes - ADK People Analytics
**Versión:** 1.0 (Enero 2026)

Este documento recopila los desafíos técnicos enfrentados, los errores críticos y las soluciones implementadas. El objetivo es servir de "Playbook" para acelerar futuros desarrollos.

---

## 🔝 Lección #1: El Cascarón del Backend (Foundation First)
**Aprendizaje:** Antes de escribir una sola línea de lógica de negocio o agentes, la infraestructura base debe estar probada y operativa.
*   **Problema:** Desarrollar features sobre una base inestable (auth a medias, conexiones inestables) multiplicó el tiempo de debugging.
*   **Acción Futura:** El Sprint 0 debe entregar:
    1.  API FastAPI operativa (`/health`).
    2.  Autenticación JWT robusta (PyJWT) y probada (`test_security.py`).
    3.  Conexiones externas (BigQuery/GCP) validadas con mocks.
    4.  Estructura de Tests (`tests/unit`, `tests/functional`) lista.

---

## 🛠️ Problemas y Soluciones Técnicas

### 1. Manejo de Datos Incompletos (Fallback)
*   **Problema:** Al consultar meses recientes (Enero 25) sin data histórica cargada, la query fallaba o devolvía error 500 al intentar dividir por cero o hacer JOIN con tablas vacías.
*   **Diagnóstico:** Asumir que `HeadcountInicial` (mes anterior) siempre existe.
*   **Solución:** Lógica de Fallback SQL con `COALESCE`.
    ```sql
    -- Si no hay HC mes anterior, usa HC actual. Si no hay ninguno, usa 0.
    COALESCE(h_ant.hc, h_act.hc, 0)
    ```

### 2. Seguridad y Obsolescencia de Librerías
*   **Problema:** Uso inicial de `python-jose`, una librería abandonada. Riesgo de seguridad.
*   **Diagnóstico:** Se usó por inercia de tutoriales antiguos de FastAPI.
*   **Solución:** Migración a **`PyJWT`** + `cryptography` (Estándar Industria).
    *   *Nota:* PyJWT usa `jwt.encode` igual que Jose, pero las excepciones cambian (`jwt.PyJWTError`).

### 3. Estrategia de Testing (Anti-Patrones)
*   **Problema:** Intentar probar lógica de negocio conectándose a BigQuery real. Lento, costoso y frágil.
*   **Solución:** Adopción estricta de **Mocks**.
    *   Tests Unitarios: Mockan *toda* llamada externa (`mock_bq_service`). Prueban que el string SQL generado sea correcto, no que BigQuery funcione.
    *   Tests Funcionales: Solo estos tocan el servidor local (`uvicorn`).

### 4. Sesión y Contexto
*   **Problema:** El agente perdía el contexto de ejecución o fallaba por "Session not found".
*   **Solución:** Inicialización robusta de sesión en `AgentRouter` y manejo sync/async adecuado para evitar condiciones de carrera en el framework ADK.

### 5. Infraestructura de Persistencia (Firestore) & IAM
*   **Problema:** Bloqueos en tests funcionales por falta de permisos en la cuenta de servicio o base de datos no inicializada.
*   **Aprendizaje (Etapa 0):** Antes de programar agentes con memoria, asegurar:
    1.  Base de datos Firestore creada en modo **Native** en GCP.
    2.  Cuenta de servicio con rol **`roles/datastore.user`**.
    3.  Nombre de DB correcto en configuración (ej. `adk-pa-firestore-db` vs `(default)`).

### 6. Integración y Contratos de Datos (Pydantic vs DB)
*   **Problema:** Error 500 en runtime (`ValidationError`) difícil de depurar porque el esquema de Firestore (`session_id`, `history`) no coincidía con el modelo estricto de ADK (`id`, `events`).
*   **Aprendizaje:**
    1.  **No asumir esquemas:** Las librerías de terceros (como Google ADK) a menudo tienen validaciones estrictas (extra='forbid').
    2.  **Mapeo Explícito:** Siempre usar adaptadores que transformen nombres de campos al cruzar fronteras (DB -> Aplicación).
    3.  **Logs de Pydantic:** Los errores de validación pueden ser silenciosos o genéricos ("Internal Server Error") si no se capturan explícitamente.

### 7. Regression Testing de Agentes (LLMOps)
*   **Problema:** Los scripts de prueba de consitencia fallaban al leer el output de las herramientas porque esperaban datos planos (dict) pero recibían objetos estructurados para UI (`ResponseBuilder`).
*   **Solución:**
    *   **Parsing Estructural:** Los tests que consumen Tools directamente deben navegar la estructura `visual_package` (`content` -> `payload`/`data` -> `kpi_row`) para extraer el dato crudo (Ground Truth).
    *   **Debug Dump:** Imprimir el JSON completo de la tool cuando falla la extracción ahorra horas de adivinanza.

### 8. Visualización Adaptativa (Frontend vs Backend)
*   **Problema:** El Agente generaba gráficos pero el frontend no los mostraba o los mostraba vacíos por falta de metadatos o nombres de columnas inconsistentes.
*   **Solución:** Estandarización mediante `ResponseBuilder`. Las herramientas de BI ahora emiten un esquema `plot` genérico (`x`, `y`, `x_label`, `y_label`) que abstrae si es Barras o Pie, asegurando que el frontend siempre tenga nombres de ejes legibles.

### 9. El Patrón "Zoom Temporal" (HU-007)
*   **Problema:** Mostrar siempre 12 meses de datos dificultaba el análisis enfocado (ej. último trimestre), creando "ruido visual" y KPIs anualizados irrelevantes para cierres mensuales.
*   **Solución:** Lógica de filtrado en el backend (Python) post-query. Traer el año completo asegura eficiencia (cache) pero el filtrado dinámico recalcula promedios, máximos y mínimos solo para el rango solicitado, devolviendo una serie de datos "quirúrgica".

### 10. Robustez contra Alucinación de Parámetros (Fix Error 500)
*   **Problema:** Un Error 500 crítico ocurría cuando el Agente intentaba cruzar filtros (ej. Talento + División) que no estaban definidos en la firma de la función. El modelo "hallucinaba" argumentos inexistentes, lanzando un `TypeError` fatal.
*   **Solución:** Implementación del patrón **`**kwargs`** en todas las herramientas del Agente. Esto permite que el sistema ignore silenciosamente cualquier parámetro extra que el modelo intente inyectar, manteniendo la estabilidad del servicio mientras se detecta la necesidad de una nueva funcionalidad.

### 11. Cruce Analítico (Feature Gaps vs Tech Errors)
*   **Aprendizaje:** Una pregunta de negocio compleja (ej. "Distribución de Hipos por División") a menudo revela la necesidad de cruces de datos que antes eran independientes.
*   **Acción:** La HU-008 resolvió esto al integrar el filtro de talento en las herramientas de distribución, convirtiendo un "error técnico" fortuito en una nueva capacidad analítica de alto valor.

### 12. Interpretación de Periodos de Negocio (Business Periods & NL)
*   **Problema:** Al pedir "último trimestre", el Agente por defecto puede tomar solo el último mes si la tool no tiene soporte explícito para rangos.
*   **Diagnóstico:** Falta de alineación entre la capacidad de "razonamiento" del modelo y la firma estricta de la función de la Tool.
*   **Solución:** 
    1.  **Parsing Robusto:** Implementar funciones de parsing de fechas (`parse_periodo`) que soporten formatos de negocio (`Q1`, `Q2`, etc.).
    2.  **Prompt Habilitador:** Instruir al Agente explícitamente sobre cómo mapear lenguaje natural ("último trimestre") a estos formatos técnicos.
    3.  **Benchmark de Rangos:** Asegurar que la lógica SQL agregue correctamente datos de múltiples meses sin corromper el cálculo de tasas (HC inicial del periodo vs Ceses acumulados).

---
**Ultima Actualización:** 30 de Enero, 2026 - Sesión: Soporte Trimestral y Cierre HU-009.
**Autores:** Equipo de Desarrollo ADK & Antigravity (IA)
