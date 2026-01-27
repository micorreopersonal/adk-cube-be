# Arquitectura de Calidad Conversacional: "Precision First"

Este documento define el marco conceptual para elevar el nivel del Agente desde un "Ejecutor de Comandos" a un "Consultor Analítico", reduciendo alucinaciones y ambigüedades.

## 1. El Problema: "The Ambiguity Gap"
Actualmente, el modelo (LLM) intenta ser "servicial" completando los vacíos de información con suposiciones (defaults).
*   **Usuario:** "Dame la rotación por UO."
*   **Agente Actual (Guessing):** "Aquí tienes la rotación de las *Divisiones* (UO2)..." (Asume UO2 arbitrariamente).
*   **Riesgo:** El usuario quería UO6 (Equipos) y toma decisiones erróneas.

## 2. Solución SOTA: Patrón "Reflective Slot Filling"

En la literatura de Agentes (tipo ReAct o CoT), implementaremos un paso intermedio de **"Reflexión de Suficiencia de Datos"**. Antes de llamar a una Tool, el agente debe validar si tiene todos los *slots* (parámetros) obligatorios llenos explícitamente.

### El Ciclo ACE (Ask-Clarify-Execute)

1.  **Analyze (Analizar):**
    *   El usuario pide "Rotación por UO".
    *   La Tool `get_turnover_deep_dive` requiere `dimension` (UO2...UO6).
    *   El agente detecta que "UO" es una categoría, no un valor específico.
2.  **Clarify (Clarificar):**
    *   En lugar de ejecutar, el agente entra en estado de **"Solicitud de Información"**.
    *   *Output:* "¿A qué nivel de profundidad te refieres? Tengo datos por Divisiones (UO2), Áreas (UO3) o Equipos (UO6)."
    *   *UX:* Se pueden sugerir "Chips" o botones de sugerencia en el Frontend.
3.  **Execute (Ejecutar):**
    *   Usuario responde: "Divisiones".
    *   Agente llama a `get_turnover_deep_dive(dimension='UO2')`.

## 3. Implementación Estructural en ADK

### A. Capa de Prompting (System Intention)
Modificaremos los prompts de los agentes (`hr_agent.py`) para prohibir las suposiciones "silenciosas".
*   **Regla:** "Si el parámetro es crítico (como la dimensión de jerarquía) y no está explícito, PREGUNTA. No asumas."

### B. Definición de Tools "Strict"
En `bq_queries/turnover.py`, definiremos los argumentos como *no-opcionales* lógicamente (aunque el código soporte defaults, el prompt obligará a llenarlos).

### C. Frontend "Active Listening"
Si el agente devuelve una pregunta aclaratoria, el Frontend debe renderizarla de forma distinta (ej. un globo de diálogo azul "Necesito más detalles") para invitar a la interacción.

## 4. Ejemplo Práctico (User Flow Propuesto)

| Paso | Actor | Acción | Contexto |
| :--- | :--- | :--- | :--- |
| 1 | Usuario | "Resumen de rotación 2025" | Ambigüedad: ¿General? ¿Por Área? |
| 2 | Agente | Analiza Tool `get_turnover`. Faltan filtros. | Decide PREGUNTAR. |
| 3 | Agente | "¿Te gustaría un resumen general de la compañía o ver el detalle por alguna División específica?" | Estado: `WAITING_INPUT` |
| 4 | Usuario | "Por División." | Ambigüedad resuelta parcialmente. |
| 5 | Agente | Llama a `get_turnover_deep_dive(dimension='UO2')`. | Ejecución Exitosa. |
