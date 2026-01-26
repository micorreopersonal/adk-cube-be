# HU-001: Análisis de Rotación Mensual (Funcional)

## 1. Criterios de Aceptación (Business Rules)
Basado en `business_inception.md` y `backlog.md`:

*   **CA1: Exclusión de Practicantes.** Todas las métricas de rotación deben filtrar y excluir el segmento "PRACTICANTE".
*   **CA2: Definición de Voluntariedad.** Un cese se considera voluntario si el campo `motivo_cese` contiene la palabra "RENUNCIA".
*   **CA3: Fórmula de Rotación.**
    *   `% Rotación = (Cesados del Mes / Headcount Inicial)`.
    *   `Headcount Inicial` = Saldo al cierre del mes anterior.
*   **CA4: Alertas de Talento.** Reportar nombre y posición de cesados con score de talento 7 (Hipers) u 8-9 (Hipos).

## 2. Flujo del Usuario
1.  El usuario pregunta: "¿Cómo cerró la rotación en [Mes]?"
2.  El Agente procesa la fecha e identifica si es para toda la compañía o una Dimensión (UO2, UO3).
3.  El Agente ejecuta las herramientas de BigQuery.
4.  El Agente responde con el formato de "Boletín Mensual".

## 3. Definición de Hecho (DoD)
*   Queries validadas contra el esquema de BigQuery.
*   Output del Agente sigue la estructura de 7 puntos del Blueprint.
*   Pruebas unitarias en `tests/` con resultado "OK".
