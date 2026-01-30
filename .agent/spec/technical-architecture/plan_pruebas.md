### DOCUMENTO: PLAN DE VALIDACIÓN DE DATOS (UAT) - BACKEND
**Objetivo:** Garantizar que las consultas generadas por el Agente coincidan con los estados financieros de talento 2025.

#### ESCENARIOS DE PRUEBA DE "VERDAD ABSOLUTA"
| ID | Caso de Prueba | Entrada (Prompt) | Valor Esperado (Referencia) |
| :--- | :--- | :--- | :--- |
| **TC-01** | Rotación General Anual | "¿Cuál fue el % de rotación total de la compañía en 2025?" | [cite_start]**37.21%** [cite: 239, 241] |
| **TC-02** | Rotación Voluntaria | "¿Qué porcentaje de las salidas en 2025 fueron renuncias?" | [cite_start]**21.18%** [cite: 270, 274] |
| **TC-03** | Segmento Talento (7,8,9) | "Dame la rotación del grupo Talento Total (7, 8 y 9) en 2025." | [cite_start]**18.79%** [cite: 707] |
| **TC-04** | Segmento HIPOS (8,9) | "¿Cómo cerró la rotación de los HIPOS (8 y 9)?" | [cite_start]**13.37%** [cite: 776] |
| **TC-05** | Pico Estacional (Mes) | "¿Cuál fue el mes con mayor rotación ADMI+FFVV y cuánto fue?" | [cite_start]**Diciembre: 4.54%** [cite: 247, 268] |
| **TC-06** | Drill-down División | "Rotación de la división Transformación en 2025." | [cite_start]**45.06%**  |
| **TC-07** | Conteo de Ceses | "¿Cuántos ceses voluntarios hubo en total?" | [cite_start]**646 personas** [cite: 275] |

#### CRITERIOS DE ACEPTACIÓN TÉCNICA:
1. [cite_start]**Lógica del Denominador:** El agente debe usar siempre el HC inicial (mes n-1) para el cálculo mensual[cite: 1258].
2. **Consistencia de Nombres:** Si el usuario pide "Ventas", el SQL debe filtrar por `EMPLEADO FFVV`.
3. **Manejo de Vacíos:** Ante unidades organizacionales sin nombre en `uo3-uo6`, el backend debe retornar "Sin Asignar" en lugar de `NULL`.