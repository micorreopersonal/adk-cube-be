# Especificación Funcional (TUS-002)

## Casos de Prueba (Golden Dataset)

| Caso ID | Pregunta (Prompt) | Tool Esperada (Ground Truth) | Tolerancia |
| :--- | :--- | :--- | :--- |
| **TC-01** | "¿Cuál fue la tasa de rotación general en Enero 2025?" | `get_monthly_attrition(month=1, year=2025)` | 0.0% (Exacto) |
| **TC-02** | "Ceses voluntarios totales en Enero 2025" | `get_monthly_attrition(...)['cesados_voluntarios']` | 0 (entero exacto) |

## Criterios de Éxito
1.  El agente **DEBE** invocar la tool correcta.
2.  El texto de respuesta debe contener el número exacto reportado por la tool.
3.  Si la Tool retorna `0.051` (5.1%), el agente debe decir "5.1%" o "5.10%", no "5%" (precisión).
