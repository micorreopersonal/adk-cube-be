# Capa de Servicios (`app/services`)

Esta carpeta contiene la implementación técnica (el "Músculo") que soporta la lógica de negocio. Se encarga de la interacción con infraestructura externa (GCP) y la generación de código ejecutable (SQL).

## Componentes Principales

### 1. Generador de Consultas (`query_generator.py`)
El motor de traducción Semántico → SQL.
*   **Input:** Métricas y Dimensiones (definidas en el Registry).
*   **Output:** SQL dialecto BigQuery optimizado.
*   **Funciones:**
    *   Mapea nombres lógicos a físicos (`registry.py`).
    *   Construye cláusulas `WHERE` seguras (Sanitización de inputs).
    *   Aplica filtros obligatorios (ej. excluir practicantes).
    *   Optimiza `GROUP BY` y `ORDER BY` según el contexto (Tendencia vs Ranking).

### 2. Conectores de Infraestructura (Singletons)
Gestionan el ciclo de vida de clientes de Google Cloud Platform.
*   `bigquery.py`: Cliente de BigQuery optimizado.
*   `firestore.py`: Cliente nativo para persistencia NoSQL.
*   `storage.py`: (Opcional) Cliente para Google Cloud Storage (documentos).

### 3. Adaptadores ADK (`adk_firestore_connector.py`)
Puente entre la librería `google.adk` (Agent Development Kit) y nuestra infraestructura.
*   **FirestoreADKSessionService:** Implementa la interfaz `SessionService` del ADK.
    *   Permite que el Agente guarde su estado/memoria en nuestro Firestore existente.
    *   Serializa/Deserializa el historial de eventos.
    *   Optimización: Carga solo los últimos 20 mensajes para reducir latencia y payloads.

---

## Flujo de Datos (Ejecución)
1.  **Agente** invoca herramienta `execute_semantic_query`.
2.  **Tool** llama a `query_generator.build_analytical_query()`.
3.  **Generator** consulta `Registry` y devuelve string SQL.
4.  **Tool** usa `BigQueryService` para ejecutar el SQL.
5.  **Resultados** (DataFrame) se retornan a la herramienta para formateo.
