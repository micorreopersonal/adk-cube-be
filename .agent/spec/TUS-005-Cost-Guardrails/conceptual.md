# TUS-005: Cost Guardrails (Protección de Presupuesto)

## Descripción Conceptual
**Como:** FinOps / Owner del Presupuesto Cloud.
**Quiero:** Que el sistema bloquee automáticamente cualquier consulta a BigQuery que exceda un límite de costo predefinido (ej. 1 GB de procesamiento).
**Para:** Evitar sorpresas de facturación por errores de programación (Cartesian Joins) o alucinaciones del Agente.

## La Solución ("Safety Circuit Breaker")
Implementar un límite duro (`hard limit`) en el cliente de BigQuery. Si una query intenta escanear una tabla completa de terabytes por error, BigQuery fallará instantáneamente con un error `400 Bad Request (Quota Exceeded)`, protegiendo la tarjeta de crédito.

## Valor del Negocio
*   **Tranquilidad:** Elimina el riesgo de "la query de los 1000 dólares".
*   **Disciplina:** Fuerza a optimizar las consultas (usar particiones `_PARTITIONDATE`).
