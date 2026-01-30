# BACKLOG TÉCNICO: LLMOps & Arquitectura

Este backlog gestiona las iniciativas de ingeniería, calidad de IA y deuda técnica.

## 🟢 COMPLETADO (DONE)

### TUS-005: Cost Guardrails (BigQuery Budget)
*   **Status:** ✅ PROTEGIDO
*   **Entregable:** `maximum_bytes_billed` + `test_cost_efficiency.py`
*   **Evidencia:** `.agent/reports/*_TUS-005_PASS.md`

### TUS-001: LLMOps - Pruebas de Regresión de Alucinación de Entidad
*   **Objetivo:** Evitar que el agente invente datos para entidades inexistentes ("Gerencia de Unicornios").
*   **Entregable:** Script `app/ai/evals/test_hallucinations.py`.
*   **Estado:** Implementado y Verificado.

---

### TUS-002: Verificación de Consistencia (Ground Truth)
*   **Objetivo:** Validar la precisión numérica comparando la respuesta del Agente vs. SQL directo.
*   **Entregable:** Script `app/ai/evals/test_data_consistency.py`.
*   **Estado:** Implementado y Verificado (Enero/Feb 2025).

---

### TUS-003: Guardrails de Dominio (Out-of-Domain)
*   **Objetivo:** Bloquear respuestas sobre temas no relacionados a RRHH (Cocina, Política, Código).
*   **Entregable:** System Prompt Guardrails + `test_domain_guardrails.py`
*   **Estado:** Implementado y Verificado.

---

### TUS-004: Pruebas Adversarias (Security & PII)
*   **Objetivo:** Pruebas de penetración de prompts (Jailbreaks) y fuga de datos sensibles (Salarios).
*   **Entregable:** System Prompt Security (Guardrails) + `test_security_adversarial.py`
*   **Estado:** Implementado y Verificado (PASS).

---

## 🟡 EN PROGRESO (DOING)
(Sin items activos)

---

## ⚪ PENDIENTE (TO DO)
