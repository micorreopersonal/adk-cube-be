# 🧹 Implementación de "Reset Session" (Limpiar Memoria)

Este documento detalla la integración del nuevo endpoint para que el usuario pueda reiniciar su conversación y borrar la memoria del agente.

## 1. Backend Endpoint Spec

*   **URL:** `POST /session/reset`
*   **Auth:** Bearer Token (Igual que `/chat`)
*   **Body (JSON):**
    ```json
    {
      "session_id": "session-admin"
    }
    ```
*   **Response (200 OK):**
    ```json
    {
      "status": "success",
      "message": "Sesión session-admin eliminada exitosamente."
    }
    ```

## 2. Instrucciones para el Frontend

### A. Ubicación del Botón
Se recomienda colocar un botón de **"Nueva Conversación"** o **"Limpiar Memoria"** en la barra superior del chat (header) o flotando cerca del input de texto.

*   **Icono Sugerido:** `TrashIcon` (Heroicons) o `RefreshIcon`.
*   **Label:** "Reiniciar Chat".
*   **Behavior:** 
    1. Llama al endpoint.
    2. Si es exitoso, **limpia la lista de mensajes local**.
    3. Muestra un toast/notificación: "Memoria del agente borrada".

### B. Prompt para Generar Código (React/Vue/Angular)

Copia y pega esto en tu asistente de código para generar la función en el frontend:

```text
Necesito una función TypeScript en mi servicio de API para llamar al endpoint de resetear sesión.

Endpoint: POST /session/reset
Payload: { session_id: string }
Headers: Authorization: Bearer <token>

Crea también un componente de UI simple (Button) que:
1. Reciba el session_id actual.
2. Al hacer click, llame a la función de reset.
3. Al terminar, emita un evento 'onReset' para que el padre limpie el chat visualmente.
Usa estilos de TailwindCSS para que parezca un botón secundario discreto (text-gray-500 hover:text-red-500).
```

### C. Ejemplo de Llamada (`curl`)
```bash
curl -X POST "http://localhost:8080/session/reset" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <TU_TOKEN>" \
     -d '{"session_id": "session-admin"}'
```
