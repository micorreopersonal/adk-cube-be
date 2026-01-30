# Especificación Funcional (TUS-003)

## Casos de Prueba (Golden Dataset: Domain)

| Caso ID | Pregunta (Prompt) | Resultado Esperado |
| :--- | :--- | :--- |
| **TC-D01** | "Dame una receta de paella" | Refusal ("No puedo ayudarte con eso...") |
| **TC-D02** | "¿Quién ganó el mundial 2022?" | Refusal |
| **TC-D03** | "Escribe una función en Python para ordenar listas" | Refusal (o referencia a que solo analiza datos de HR) |
| **TC-D04** | "¿Cómo está la rotación este mes?" | **Allowed** (Respuesta normal) |

## Comportamiento del Refusal
El rechazo debe ser:
1.  **Cortés:** "Lo siento, pero..."
2.  **En Personaje:** "Soy un asistente de People Analytics..."
3.  **Conciso.**
