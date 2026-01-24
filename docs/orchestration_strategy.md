# Estrategia de Orquestación: People Analytics AI

## 1. Arquitectura de Agentes
Se adopta el patrón **Multi-Agente Especialista** orquestado por un **Router**.

### 1.1. Router (Director de Orquesta)
*   **Responsabilidad:** Triage de intención inicial.
*   **Lógica:** Determina si la consulta es sobre métricas numéricas (BigQuery) o sobre documentos normativos (GCS).
*   **Herramientas:** Ninguna. Su única tool es el `AgentTransfer`.

### 1.2. HR Agent (Especialista en Datos)
*   **Responsabilidad:** Análisis de rotación, dotación, talento y proyecciones.
*   **Orquestación interna:** Uso de **Atomic Tools**. Cada métrica es una herramienta de Python que ejecuta una query específica.
*   **¿Por qué no sub-agentes?** No es necesario dividir este agente ya que el contexto de negocio (Rotación) es coherente y las herramientas comparten los mismos filtros de seguridad (exclusión de practicantes).

### 1.3. Docs Agent (Especialista en Políticas)
*   **Responsabilidad:** Responder dudas sobre el Reglamento Interno, Políticas de Beneficios, etc.
*   **Orquestación interna:** RAG (Retrieval-Augmented Generation) sobre buckets de Google Cloud Storage.

## 2. Decision Tree para Sub-agentes
Solo se creará un sub-agente nuevo si se cumple alguna de estas condiciones:
1.  **Cambio de Contexto Drástico:** Ejemplo: Un asistente para agendar entrevistas que requiere acceso a Calendario (permisos distintos).
2.  **Conflicto de Prompts:** Cuando las instrucciones de un especialista confunden al otro (ej: instrucciones de anonimización muy estrictas para nómina vs datos agregados de rotación).
3.  **Seguridad (Data Silos):** Si el agente `hr_agent` no debe tener acceso a datos de salarios individuales, se crea un `payroll_agent` con credenciales restringidas.

## 3. Flujo de Ejecución (Run Rate)
1.  **Input:** Conversación vía FastAPI.
2.  **Router:** Clasifica y transfiere al agente meta.
3.  **Especialista:** Ejecuta tools, sintetiza y responde en Markdown.
4.  **Memoria:** Se utiliza `InMemorySessionService` (ADK) para mantener el hilo de la conversación.
创新
