# Estado Operativo del Proyecto: ADK People Analytics

**Fecha de Corte:** 2026-01-24
**Versión:** 1.0 (MVP HU-001)

## 1. Resumen de Componentes Activos

| Componente | Estado | Descripción |
| :--- | :---: | :--- |
| **Backend API** | ✅ Activo | FastAPI corriendo en puerto 8000. |
| **BigQuery Link** | ✅ Conectado | Acceso verificado a `adk-team-fitness.fact_hr_rotation`. |
| **Orquestador** | ✅ Activo | `AgentRouter` gestionando sesiones con ADK Runner. |
| **Agente HR** | ✅ Activo | Especialista configurado con tools de rotación y alertas. |
| **Tests** | ✅ Pasados | Cobertura de lógica de negocio y endpoints (4/4 tests OK). |

---

## 2. Capacidades Funcionales (Qué puede hacer la IA ahora)

1.  **Cálculo de Rotación:**
    *   Calcula Tasa General y Voluntaria.
    *   Filtra automáticamente "PRACTICANTE".
    *   Identifica renuncias voluntarias por texto (`motivo_cese` like '%RENUNCIA%').

2.  **Segmentación:**
    *   Distingue entre fuerza de ventas (FFVV) y administrativos (ADMI).

3.  **Alertas de Talento:**
    *   Detecta salidas de empleados clave (Score 7, 8, 9).

---

## 3. Payloads de Prueba para Swagger

Copia y pega estos JSONs en el endpoint `POST /chat` (`http://127.0.0.1:8000/docs`).

### Caso A: Consulta General de Rotación
**Pregunta:** "¿Cuál fue la tasa de rotación general en enero 2025?"
```json
{
  "message": "¿Cuál fue la tasa de rotación general en enero de 2025?",
  "session_id": "test-session-001",
  "context_profile": "EJECUTIVO"
}
```

### Caso B: Comparativa de Segmentos (ADMI vs FFVV)
**Pregunta:** "Dame la rotación voluntaria de ADMI comparada con FFVV."
```json
{
  "message": "Analiza la rotación voluntaria de ADMI vs FFVV para enero 2025.",
  "session_id": "test-session-002",
  "context_profile": "ANALISTA"
}
```

### Caso C: Alerta de Fuga de Talento
**Pregunta:** "Dime los nombres de Hipers e Hipos que renunciaron."
```json
{
  "message": "¿Qué talento clave (Hipers o Hipos) perdimos el mes pasado?",
  "session_id": "test-session-003",
  "context_profile": "ADMIN"
}
```

---

## 4. Troubleshooting
Si encuentras errores:
*   **Error 500:** Verifica que `verify_bq_connection.py` siga dando "Éxito".
*   **Respuesta vacía:** Verifica que el mes solicitado tenga datos en `fact_hr_rotation`.
