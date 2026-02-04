# Capa de API (`app/api`)

Esta carpeta expone la funcionalidad del sistema al mundo exterior mediante **FastAPI**. Define los endpoints REST, maneja la autenticación (JWT) y gestiona el ciclo de vida de las peticiones HTTP.

## Componentes Principales

### 1. Enrutador (`routes.py`)
Es el único archivo de definición de rutas. Centraliza todos los endpoints para mantener la simplicidad.

#### Endpoints Públicos / Utilidad
*   `GET /`: Health check básico. Devuelve proyecto, entorno y estado.
*   `GET /health`: Estado de salud para orquestadores (Cloud Run).

#### Endpoints de Seguridad (OAuth2)
*   `POST /token`: **Login**.
    *   Recibe: `username`, `password` (Form Data).
    *   Valida: Contra `app/core/mock_users.py` (o base de datos futura).
    *   Retorna: `access_token` (JWT) con el perfil del usuario (`admin`, `ejecutivo`) embebido.

#### Endpoints Core (Chat)
*   `POST /chat`: **Interacción Principal**.
    *   Protección: Requiere Header `Authorization: Bearer <token>`.
    *   Input: `ChatRequest` (Mensaje, SessionID).
    *   Proceso: Invoca al `AgentRouter` de la capa de IA.
    *   Output: `ChatResponse` (Texto + `VisualDataPackage`).
*   `POST /session/reset`: Limpia la memoria de la conversación en Firestore para empezar de cero.

#### Endpoints de Infraestructura (Test)
*Exclusivos para depuración y validación de conectividad Cloud.*
*   `GET /test/bigquery`: Prueba conexión a BQ ejecutando `SELECT 1`.
*   `GET /test/storage`: Lista archivos en el bucket de documentos.
*   `GET /test/firestore`: Escribe y lee un documento de prueba.

---

## Flujo de Petición
1.  **Request:** Cliente envía HTTP POST con Token.
2.  **Auth (Dependency):** FastAPI valida firma y expiración del JWT (`get_current_user`).
3.  **Controller:** `routes.py` extrae el perfil del usuario del token.
4.  **Service:** Llama a `ai_router.route(msg, profile=user.profile)`.
5.  **Response:** Serializa la respuesta del agente a JSON estándar.
