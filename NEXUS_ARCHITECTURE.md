# 🧠 Arquitectura Nexus v2.1: El Corazón Analítico

Este documento detalla el flujo funcional de **ADK Talent Analytics** y las propiedades vitales que permiten la traducción de lenguaje natural a decisiones de negocio.

## 1. El Flujo de Atención (Step-by-Step)
Cuando un usuario realiza una solicitud, el sistema activa una cadena de inteligencia en tres capas:

### Capa A: Orquestación de Sesión y Triaje
1.  **Recepción y Filtro**: El [router_logic.py](file:///c:/adk-projects/adk-people-analytics-backend/app/ai/agents/router_logic.py) recibe el mensaje. Si es un saludo trivial, responde por "vía rápida" para ahorrar latencia.
2.  **Validación de Slots**: Si es una consulta de datos, el Agente de Triaje asegura que existan los 3 elementos vitales (**Métrica, Estructura y Periodo**). Si faltan, los recolecta conversacionalmente.
3.  **Exploración Orgánica**: Si el usuario pregunta qué hay disponible, se activa `list_organizational_units` en [triage_validator.py](file:///c:/adk-projects/adk-people-analytics-backend/app/ai/tools/triage_validator.py) para leer BigQuery en tiempo real.

### Capa B: Razonamiento Experto (Expert Layer)
1.  **Cerebro Semántico**: Una vez validados los datos, el control pasa a [hr_agent.py](file:///c:/adk-projects/adk-people-analytics-backend/app/ai/agents/hr_agent.py).
2.  **Contexto Temporal**: El agente inyecta la fecha actual para entender conceptos como "este trimestre" o "el mes pasado".
3.  **Mapeo de Nombres**: Se resuelven ambigüedades culturales (ej: "Personas" -> "DIVISION SEGUROS PERSONAS") usando reglas de sinónimos explícitas.

### Capa C: Ejecución y Visualización
1.  **Consumo del Registro**: El agente selecciona métricas y dimensiones de [registry.py](file:///c:/adk-projects/adk-people-analytics-backend/app/core/analytics/registry.py) (la única fuente de verdad SQL).
2.  **Construcción de Queries**: [query_generator.py](file:///c:/adk-projects/adk-people-analytics-backend/app/services/query_generator.py) ensambla el SQL seguro, aplicando límites de alta cardinalidad (hasta 1000 filas) y filtros obligatorios.
3.  **Empaquetado Visual**: [universal_analyst.py](file:///c:/adk-projects/adk-people-analytics-backend/app/ai/tools/universal_analyst.py) ejecuta la consulta y transforma el DataFrame resultante en un `VisualDataPackage`.

---

## 📂 Archivos Vitales del Ecosistema

| Archivo | Función Vital | Ver Archivo |
| :--- | :--- | :--- |
| **Router Logic** | Orquestador de sesión y triaje inicial. | [Ver](file:///c:/adk-projects/adk-people-analytics-backend/app/ai/agents/router_logic.py) |
| **HR Agent** | Prompt Maestro y lógica de negocio/semántica. | [Ver](file:///c:/adk-projects/adk-people-analytics-backend/app/ai/agents/hr_agent.py) |
| **Semantic Registry** | Diccionario oficial de Métricas y Dimensiones SQL. | [Ver](file:///c:/adk-projects/adk-people-analytics-backend/app/core/analytics/registry.py) |
| **Query Generator** | Traductor de Semántica a SQL BigQuery. | [Ver](file:///c:/adk-projects/adk-people-analytics-backend/app/services/query_generator.py) |
| **Universal Analyst** | Ejecutor y formateador de Visual Data Packages. | [Ver](file:///c:/adk-projects/adk-people-analytics-backend/app/ai/tools/universal_analyst.py) |
| **Triage Validator** | Validación de estructura organizacional. | [Ver](file:///c:/adk-projects/adk-people-analytics-backend/app/ai/tools/triage_validator.py) |

---

## 🏆 Atributos de la Solución Nexus v2.1
*   **Source of Truth**: Fórmulas auditadas en [registry.py](file:///c:/adk-projects/adk-people-analytics-backend/app/core/analytics/registry.py).
*   **Eficiencia**: Capa de soporte para variaciones de nombres de gráficos en [universal_analyst.py](file:///c:/adk-projects/adk-people-analytics-backend/app/ai/tools/universal_analyst.py).
*   **Memoria**: Persistencia de slots vía **Firestore** gestionada en [router_logic.py](file:///c:/adk-projects/adk-people-analytics-backend/app/ai/agents/router_logic.py).

---
*Manual interactivo generado para Antigravity IDE - Nexus v2.1 Evolution.*
