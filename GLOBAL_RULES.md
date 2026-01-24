# GLOBAL RULES & ARCHITECTURE - ADK People Analytics Backend

Este documento consolida las reglas de comunicación, arquitectura y seguridad para el desarrollo del ecosistema de IA utilizando **Google Agent Development Kit (ADK)**.

---

## 1. Reglas Generales de Comunicación
*   **Idioma:** Toda comunicación, documentación y comentarios de código deben ser en **Español**.
*   **Rol:** El asistente actúa como un experto desarrollador Python.
*   **Flujo de Código:** Los cambios de código se entregan de manera **secuencial (paso a paso)** para que el usuario pueda copiar y pegar. No se realizan cambios directos a menos que se instruya explícitamente.

---

## 2. Arquitectura del Backend ADK
La estructura del proyecto sigue un patrón modular nativo de GCP:

```text
/
├── app/
│   ├── agents/             # Lógica de agentes (Google ADK)
│   │   ├── router.py       # Orquestador (Triage de intención)
│   │   ├── hr_agent.py     # Especialista en Análisis de Rotación
│   │   └── docs_agent.py   # Especialista en Documentación/Políticas
│   ├── tools/              # Herramientas atómicas (Tool-use)
│   │   ├── bq_queries/     # Consultas SQL optimizadas para Attrition
│   │   ├── gcs_handlers/   # Procesamiento de Excel y PDFs
│   │   └── common.py       # Utilidades transversales
│   ├── services/           # Clientes de Infraestructura (Singleton)
│   │   ├── bigquery.py     # Gestión de conexiones a BQ
│   │   ├── storage.py      # Gestión de buckets GCS
│   │   └── firestore.py    # Persistencia de estado de sesión
│   ├── core/               # Núcleo del Sistema
│   │   ├── config.py       # Validación de variables de entorno (Pydantic)
│   │   └── security.py     # Filtros de anonimización (RUT/Salarios)
│   └── main.py             # Punto de entrada FastAPI
├── docs/                   # Documentación de Metodología (HUs)
├── tests/                  # Pruebas de integridad de lógica
├── .env                    # Configuración de secretos local
├── requirements.txt        # Dependencias de Python
└── Dockerfile              # Empaquetado para Cloud Run
```

---

## 3. Reglas de Desarrollo
*   **Backend:** FastAPI estricto. La lógica de negocio debe residir en la "Service Layer", no en los endpoints.
*   **Estado:** La aplicación debe ser **Stateless** (diseñada para Cloud Run). La persistencia de sesión se maneja en **Firestore**.
*   **GCP Native:** Uso de BigQuery para datos de rotación y Cloud Storage para documentos normativos.

---

## 4. Seguridad y Hard Constraints
*   **Credenciales:** Prohibido el hardcodeo de credenciales. Usar siempre `os.environ` o Secret Manager.
*   **Anonimización:** Cualquier dato sensible como **RUT** o **Salarios** debe ser anonimizado en los logs.
*   **Límites de DB:** El agente tiene prohibido ejecutar operaciones `DELETE` en BigQuery.

---

## 5. Blueprint de Configuración (.env)
```env
PROJECT_ID=tu-proyecto-id
REGION=us-central1
BQ_DATASET=hr_analytics
BQ_TABLE_TURNOVER=attrition_table
GCS_BUCKET_DOCS=hr-docs-bucket
GCS_BUCKET_LANDING=hr-data-landing
FIRESTORE_COLLECTION=agent_sessions
LOG_LEVEL=INFO
ENV=development
```
