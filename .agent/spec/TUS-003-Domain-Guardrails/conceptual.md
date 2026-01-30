# TUS-003: Guardrails de Dominio (Out-of-Domain)

## Descripción Conceptual
**Como:** Security Officer / Product Owner.
**Quiero:** Que el Agente se niegue a responder preguntas que no estén relacionadas con Recursos Humanos, Análisis de Datos o la Empresa.
**Para:** Evitar uso indebido (generar código, recetas, opiniones políticas) y mantener la identidad corporativa.

## Límites del Dominio
*   **Permitido (In-Domain):**
    *   Rotación, HC, Talento, Métricas.
    *   Preguntas sobre definiciones del dashboard.
    *   Saludos y conversación básica de cortesía ("Hola", "¿Quién eres?").
*   **Prohibido (Out-of-Domain):**
    *   Generación de código Python/HTML (salvo explicación de queries SQL internas).
    *   Preguntas de cultura general ("Capital de Francia").
    *   Asesoría médica, legal o financiera personal.

## La Solución ("Instruction Tuning")
El método principal será reforzar el **System Prompt**. No usaremos modelos clasificadores externos por latencia, sino instrucciones estrictas de "Role-Playing".
