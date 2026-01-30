# Especificación Funcional (TUS-005)

## Reglas de Negocio
1.  **Límite por Query:** Ninguna consulta individual puede procesar más de **1 Gigabyte (10^9 bytes)**.
    *   *Rationale:* Las consultas de HR Analytics suelen ser agregadas y eficientes. 1 GB es suficiente para análisis normales pero bloquea full scans masivos accidentales.
2.  **Comportamiento en Fallo:**
    *   El sistema debe capturar el error `bytesBilledLimitExceeded`.
    *   El Agente debe informar al usuario: "La consulta es demasiado costosa para mis límites de seguridad. Por favor intenta reducir el rango de fechas".

## Casos de Prueba (Cost Efficiency)
| Caso ID | Escenario | Resultado Esperado |
| :--- | :--- | :--- |
| **TC-C01** | Query Optimizado (Filtro por Mes) | **PASS** (< 100 MB escaneados) |
| **TC-C02** | Full Scan (SELECT * FROM BigTable) | **BLOCK** (Error por límite de bytes) |
| **TC-C03** | Dry Run Verification | Estimación precisa de bytes antes de ejecución. |
