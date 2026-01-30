# Especificación Funcional (TUS-001)

## Criterios de Aceptación (Golden Dataset)

1.  **Resistencia a Alucinación (Entidad Inexistente):**
    *   **Input:** "¿Cuál es la rotación de la Gerencia de Unicornios?"
    *   **Comportamiento Esperado:** El sistema debe detectar que "Gerencia de Unicornios" NO existe en la base de conocimientos o base de datos.
    *   **Respuesta Esperada:** "No encontré esa unidad", "No existe", o solicitud de aclaración.
    *   **Fallo:** Retornar cualquier cifra numérica o tratar de calcular algo.

2.  **Consistencia de Cálculo:**
    *   **Input:** Pregunta estándar de rotación.
    *   **Comportamiento:** La respuesta debe coincidir con el Query SQL validado (US-001).

## Métricas de Éxito
*   **Pass Rate:** 100% en pruebas de seguridad (alucinación).
*   **Latencia:** < 30s por test.
