# Changelog de LLMOps

Este log registra las capacidades operativas agregadas al ecosistema ADK (Backend).

## [2026-01-30]
### Added
*   **TUS-005 (Cost Guardrails):** Implementación de límites de facturación en BigQuery Client (1 GB per query).
    *   `app/services/bigquery.py`: `maximum_bytes_billed` configurado.
    *   `app/ai/evals/test_cost_efficiency.py`: Test de regresión (Dry Run).
*   **TUS-001 (Hallucination Resisitance):** Refinamiento de script de pruebas para aceptar negativas válidas ("No tengo acceso").

## [2026-01-29]
### Added
*   **TUS-003 (Domain Guardrails):** Bloqueo de preguntas fuera de dominio (Cocina, Política). Validado con `test_domain_guardrails.py`.
*   **TUS-004 (Security):** Protección contra PII Leaks y Jailbreaks. Validado con `test_security_adversarial.py`.

## [2026-01-28]
### Added
*   **TUS-002 (Data Consistency):** Verificación ground-truth vs respuesta del agente para KPIs de rotación.
