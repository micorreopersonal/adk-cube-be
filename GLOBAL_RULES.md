# GLOBAL RULES & ARCHITECTURE - ADK People Analytics Backend

Este documento consolida las reglas de comunicación, arquitectura y seguridad para el desarrollo del ecosistema de IA utilizando **Google Agent Development Kit (ADK)** bajo el patrón **Semantic Cube**.

---

## 1. Reglas Generales de Comunicación
*   **Idioma:** Toda comunicación, documentación y comentarios de código deben ser en **Español**.
*   **Rol:** El asistente actúa como un experto desarrollador Python.
*   **Flujo de Código:** Los cambios de código se entregan de manera **secuencial (paso a paso)** para que el usuario pueda copiar y pegar. No se realizan cambios directos a menos que se instruya explícitamente.

---

## 2. Arquitectura del Backend ADK (SOTA 2026)

La estructura del proyecto sigue un patrón modular **Semantic Cube**, separando la inteligencia probabilística (AI) de la lógica determinística (Services).

```text
/
├── app/
│   ├── ai/                 # CEREBRO (Capa Probabilística)
│   │   ├── agents/         
│   │   │   ├── router_logic.py  # Orquestador Inteligente (Triage & Memory)
│   │   │   └── hr_agent.py      # Agente Semántico (Context-Aware)
│   │   └── tools/          
│   │       ├── universal_analyst.py # Herramienta Universal (Text-to-SQL + Viz)
│   │       └── triage_validator.py  # Validaciones de baja latencia
│   │
│   ├── core/               # CORAZÓN (Definiciones y Seguridad)
│   │   ├── analytics/      
│   │   │   └── registry.py      # Semantic Registry (Single Source of Truth)
│   │   ├── config.py       # Pydantic Settings
│   │   └── security.py     # RBAC y Auth
│   │
│   ├── services/           # MÚSCULO (Capa Determinística)
│   │   ├── query_generator.py   # Motor de construcción SQL Seguro
│   │   ├── adk_firestore_connector.py # Gestión de Sesiones ADK
│   │   └── bigquery.py     # Cliente BQ Singleton
│   │
│   ├── api/                # PUERTA DE ENLACE
│   │   └── routes.py       # Endpoints FastAPI
│   └── main.py             # Entrypoint
│
├── docs/                   # MEMORIA INSTITUCIONAL
│   ├── CAPABILITIES.md     # Resumen de Capacidades Técnicas
│   └── setup/              # Guías de despliegue
│
├── tests/                  # ASEGURAMIENTO DE CALIDAD
│   └── test_semantic_core.py # Suite Unificada (Pytest)
├── .env                    # Secretos Locales
└── Dockerfile              # Runtime Cloud Run
```

---

## 3. Reglas de Desarrollo
*   **Semantic First:** Toda métrica nueva DEBE ser registrada primero en `app/core/analytics/registry.py` antes de ser usada por el agente.
*   **Stateless by Design:** La aplicación no guarda estado en memoria local. Todo contexto conversacional reside en **Firestore**.
*   **Visual-Data-Package:** Las herramientas analíticas no retornan texto plano, sino objetos estructurados (`VisualDataPackage`) listos para renderizar componentes UI (Gráficos, Tablas, KPIs).

---

## 4. Seguridad y Hard Constraints
*   **Anti-Alucinación:** Prohibido que el LLM genere SQL directo ("Text-to-SQL" crudo). Debe usar el `query_generator` que valida contra el Registry.
*   **Filtros Obligatorios:** El sistema inyecta automáticamente filtros de seguridad (ej. excluir practicantes) en TODAS las consultas, invisible para el agente.
*   **Anonimización (Contexto Perú):**
    *   **Identificadores:** Todo **DNI** o **CE** debe ser enmascarado en logs (ej. `XX.XXX.XXX-X`).
    *   **Sueldos:** Los valores monetarios de salarios deben ser ocultados (`[SALARIO_CONFIDENCIAL]`).
*   **Credenciales:** Prohibido hardcodeo. Uso estricto de `os.environ`.

---

## 5. Blueprint de Configuración (.env)
```env
PROJECT_ID=tu-proyecto-id
REGION=us-central1
BQ_DATASET=hr_analytics
BQ_TABLE_TURNOVER=attrition_table
GCS_BUCKET_DOCS=hr-docs-bucket
FIRESTORE_COLLECTION=agent_sessions
LOG_LEVEL=INFO
GOOGLE_GENAI_USE_VERTEXAI=true
```

---

## 6. Políticas de Calidad (Testing)
*   **Test-Driven Refactor:** Antes de modificar el núcleo semántico (`query_generator` o `universal_analyst`), se debe ejecutar `pytest tests/test_semantic_core.py` para asegurar no romper la integridad de las métricas.
*   **Sanidad de Métrica:** Verificar siempre que las fórmulas SQL en `registry.py` coincidan con la definición de negocio (ej. "Activo" vs "Cesado").

---

## 7. Estrategia de Orquestación (Router)
*   **Triage Rápido:** `AgentRouter` utiliza `gemini-2.0-flash` para detectar intención y slots (Periodo, Estructura) sin invocar herramientas pesadas.
*   **Specialized Hand-off:** Una vez clara la intención, se delega al `hr_agent` con el contexto ya cargado (“Hot-Start”).
