# Capa de Inteligencia (`app/ai`)

Esta carpeta contiene el **"Cerebro Probabilístico"** del sistema. Aquí reside la lógica de agentes, orquestación y las herramientas que conectan el lenguaje natural con los servicios determinísticos.

## Arquitectura de Agentes (Semantic Cube)

La arquitectura sigue un patrón de **Router-Expert** para minimizar la latencia y maximizar la precisión.

### 1. Orquestación (`agents/router_logic.py`)
Es la puerta de entrada. No resuelve dudas complejas, sino que **clasifica** y **prepara** la sesión.
*   **Rol:** Triage rápido (usando `gemini-2.0-flash`).
*   **Funciones:**
    *   **Slot Filling:** Extrae Periodo, Estructura (Área/División) y Formato deseado.
    *   **Fast-Path:** Responde saludos sin gastar cuota de herramientas.
    *   **Memory:** Mantiene el contexto de la conversación ("triage slots") en Firestore.
    *   **Handoff:** Una vez tiene los slots necesarios, inicializa y cede el control al `HR_Semantic_Agent`.

### 2. El Experto (`agents/hr_agent.py`)
Es el agente especialista en Recursos Humanos.
*   **Rol:** Traductor Semántico (Natural Language -> Semantic Request).
*   **Configuración:**
    *   Prompt dinámico (`HR_PROMPT_SEMANTIC`) que inyecta métricas del Registry y dimensiones reales.
    *   Reglas de Negocio "Hard-Coded" en el prompt (ej. "Si piden 'Lista', usa 'TABLE'").
    *   **Privacidad:** Instruido para rechazar preguntas de sueldos y saber que el sistema anonimiza automáticamente.

---

## Catalog de Herramientas (`tools/`)

### 1. Universal Analyst (`universal_analyst.py`)
La herramienta "navaja suiza" del agente experto.
*   **Input:** `SemanticRequest` (JSON con métricas, dimensiones y filtros).
*   **Proceso:**
    1.  Valida la solicitud contra el `Registry`.
    2.  Genera SQL seguro mediante `query_generator`.
    3.  Ejecuta en BigQuery.
    4.  **Data Masking:** Aplica máscaras de privacidad (DNI, Salarios) en esta capa.
    5.  Formatea la respuesta en bloques visuales (`VisualDataPackage`).
*   **Output:** Gráficos, Tablas y KPIs listos para renderizar.

### 2. Triage Validator (`triage_validator.py`)
Herramientas ligeras para el Router (Fase de Exploración).
*   **Objetivo:** Validar existencia de unidades o disponibilidad de datos *antes* de lanzar una consulta pesada.
*   **Funciones:** `list_organizational_units`, `validate_dimensions`.

---

## Flujo de Conversación Típico

1.  **Usuario:** "Dame la rotación de Finanzas en 2024"
2.  **Router:** Detecta `structure='Finanzas'`, `period='2024'`. Pasa a modo "Ready".
3.  **Handoff:** Se invoca a `HR_Semantic_Agent` con el contexto ya cargado.
4.  **Agente:** Traduce a `execute_semantic_query(intent='TREND', filters=[...])`.
5.  **Universal Analyst:** Genera SQL → BigQuery → Retorna JSON Visual.
6.  **Frontend:** Renderiza el Gráfico de Línea.
