# Guía de Pruebas de API - ADK HR Agent

Este documento describe cómo interactuar con los endpoints del Agente de HR, autenticarse y ejecutar los casos de prueba definidos.

## 1. Configuración de Entorno
*   **Base URL:** `http://127.0.0.1:8000` (Localhost)
*   **Documentación Interactiva (Swagger):** `http://127.0.0.1:8000/docs`

## 2. Autenticación (JWT)
El acceso al chat está protegido. Debes obtener un token antes de realizar consultas.

### Obtener Token
*   **Endpoint:** `POST /token`
*   **Content-Type:** `application/x-www-form-urlencoded`

| Campo | Valor (Dev) |
| :--- | :--- |
| `username` | `admin` |
| `password` | `p014654` |

**Respuesta Exitosa (200 OK):**
```json
{
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "token_type": "bearer"
}
```

### Usar Token
En todas las peticiones a `/chat`, incluye el header:
`Authorization: Bearer <tu_access_token>`

---

## 3. Casos de Prueba (Payloads)
Endpoint: `POST /chat`

### Caso A: Rotación General (Perfil EJECUTIVO)
Consulta simple de métricas agregadas.
```json
{
  "message": "¿Cuál fue la tasa de rotación general en enero de 2025?",
  "session_id": "manual-test-001",
  "context_profile": "EJECUTIVO"
}
```

### Caso B: Comparativa de Segmentos (Perfil ANALISTA)
Análisis comparativo entre fuerzas de ventas y administrativos.
```json
{
  "message": "Analiza la rotación voluntaria de ADMI vs FFVV para enero 2025.",
  "session_id": "manual-test-002",
  "context_profile": "ANALISTA"
}
```

### Caso C: Alerta de Talento (Perfil ADMIN)
Solicitud de información sensible (nombres de Hipers/Hipos).
```json
{
  "message": "¿Qué talento clave (Hipers o Hipos) perdimos en enero 2025?",
  "session_id": "manual-test-003",
  "context_profile": "ADMIN"
}
```

### Caso D: Boletín Mensual Completo (Perfil ANALISTA/ADMIN)
**Nuevo:** Generación de un reporte consolidado con todos los insights.
```json
{
  "message": "Genera el reporte mensual de rotación de enero 2025. Incluye métricas generales, comparativa por segmentos (FFVV vs ADMI) y detalle de fugas de talento clave (Hipers/Hipos).",
  "session_id": "manual-test-report",
  "context_profile": "ANALISTA"
}
```

---

## 4. Ejecución Automatizada
Para correr la suite de pruebas completa:
```bash
python tests/functional/test_chat_flow.py  # Casos A, B, C
python tests/functional/test_full_report.py # Caso D (Boletín)
```
