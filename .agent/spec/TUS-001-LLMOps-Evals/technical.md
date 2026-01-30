# Especificación Técnica (TUS-001)

## Arquitectura de Pruebas
Las pruebas se ejecutan como scripts de cliente externo (`requests`) contra la API del Agente (`localhost`).

*   **Ubicación:** `app/ai/evals/`
*   **Framework:** `pytest` (para aserciones y reportes).
*   **Bypass de Auth:** Uso del token `dev-token-mock` para evitar flujos de SSO complejos en CI/CD local.

## Implementación de Referencia
*   **Script:** `test_hallucinations.py`
*   **Validación:** Búsqueda de keywords de éxito ("no existe", "no encontré") vs keywords de fallo ("tasa del", "es de X%").

## CI/CD Pipeline (Futuro)
Estas pruebas deben bloquear el PR si fallan (Gatekeeper).
