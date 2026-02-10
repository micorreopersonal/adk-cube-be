# Resumen de Capacidades: ADK Talent Analytics Backend

Este documento resume las capacidades actuales del backend del proyecto **People Analytics**, diseñado bajo la arquitectura SOTA 2026 de Google Agent Development Kit (ADK).

---

## 1. Arquitectura & Core

### **Modelo de Ejecución**
*   **Diseño Stateless**: Optimizado para **Cloud Run**.
*   **Sesiones Persistentes**: Gestión de estado y contexto de conversación vía **Firestore**.
*   **Orquestador Inteligente (`AgentRouter`)**:
    *   **Triage de Baja Latencia**: Modelo ligero (`gemini-2.0-flash`) para saludos y recolección rápida de slots (Periodo, Estructura, Formato).
    *   **Router Dinámico**: Asigna el agente especializado según el perfil del usuario (EJECUTIVO, ANALISTA, etc.).
    *   **Resiliencia**: Manejo automático de reintentos por límites de cuota (429) y errores transitorios.

### **Seguridad y Gobernanza**
*   **Registry Centralizado**: `app/core/analytics/registry.py` actúa como la *Single Source of Truth* para métricas y dimensiones.
    *   **Métricas**: Definiciones SQL explícitas (ej. Tasa de Rotación, Costo de Rotación, Headcount).
    *   **Dimensiones**: Mapeo controlado de campos (ej. `uo2` -> División, `uo3` -> Área).
*   **Filtros Obligatorios**: Inyección automática de reglas de seguridad (ej. Exclusión de practicantes) en todas las queries.

---

## 2. Inteligencia Artificial (Cerebro)

### **Agente Semántico (`HR_Semantic_Agent`)**
*   **Traducción de Negocio**: Convierte preguntas en lenguaje natural a solicitudes JSON estructuradas (`SemanticRequest`).
*   **Context-Aware**:
    *   Conoce la fecha actual y el "último mes cerrado".
    *   Inyecta dinámicamente las divisiones reales disponibles en la base de datos.
*   **Intenciones Soportadas**:
    *   `TREND`: Análisis de evoluciones temporales (Líneas).
    *   `COMPARISON`: Comparativas entre categorías o periodos (Barras).
    *   `SNAPSHOT`: KPIs puntuales o fotos del momento.
    *   `LISTING`: Listados detallados de colaboradores (Tablas).

### **Herramientas (`Tools`)**
*   **`execute_semantic_query` (Universal Analyst)**:
    *   **Generación SQL**: Convierte el request semántico en SQL optimizado para BigQuery.
    *   **Smart Limits**: Protege el sistema limitando automáticamente queries grandes (ej. listados > 50 filas) y advirtiendo al usuario.
    *   **Smart Visualization**: Auto-selecciona la mejor visualización (`KPI_ROW`, `LINE_CHART`, `BAR_CHART`, `TABLE`) basada en la naturaleza de los datos.
    *   **Corrección de Errores**: Capa de resiliencia para corregir alucinaciones comunes del LLM antes de ejecutar.

### **Reportes Inteligentes**
*   **Reporte Ejecutivo de Rotación**:
    *   **Generación Orquestada**: Secuencia de 7 bloques analíticos (Headline, Segmentación, Focos, Talento, etc.).
    *   **Context-Aware AI**: Los insights generados por el LLM reciben datos reales extraídos en memoria de los gráficos y tablas (no "ciegos").
    *   **Comparativas Automáticas**: Cálculo de variaciones vs promedio anual o peridos anteriores.
    *   **Generación Modular (Atomic Testing)**: Capacidad de generar secciones aisladas (ej. solo "segmentation") para refinamiento rápido de prompts.

---

## 3. Servicios de Datos (Músculo)

### **Motor de Consultas (`query_generator.py`)**
*   **Abstracción SQL**: Construye queries ANSI SQL seguras sin exponer la estructura física de la BD al LLM.
*   **Optimizaciones**:
    *   Ordenamiento inteligente (Cronológico para tendencias, Ranking para comparativas).
    *   Manejo eficiente de agregaciones `GROUP BY`.
    *   Filtros `CASE-INSENSITIVE` automáticos.

### **Catálogo de Datos Disponible**
*   **Métricas Clave**:
    *   Rotación (Global, Voluntaria, Involuntaria).
    *   Ceses (Totales y desglosados).
    *   Costo Estimado de Rotación.
    *   Headcount Promedio.
*   **Dimensiones**:
    *   **Organizacional**: División, Área, Posición, Nombre.
    *   **Temporal**: Año, Mes, Trimestre, Semestre, Fecha Cese.
    *   **Segmentación**: Talento (Performance), Motivo de Cese, Segmento, Salario.

---

## 4. API & Integración

*   **FastAPI**: Framework de alto rendimiento.
*   **Endpoints**:
    *   `/chat`: Endpoint principal para interacción con agentes.
    *   Integración preparada para Frontend moderno.
*   **Observabilidad**: Logs detallados de Tiempos de Ejecución (Timing Breakdown) y costos estimados (Tokens/Slots).

---

## 5. Ejemplos de Consultas (Demo Script)

### 🟢 Básicas (Atómicas)
1.  **KPI Global**: *"¿Cuál es la tasa de rotación acumulada en 2025?"*
2.  **Filtro por División**: *"Dime los ceses totales en Finanzas."*
3.  **Métrica Calculada**: *"¿Cuál es el costo estimado de rotación en Tecnología?"*
4.  **Drill-down**: *"¿Cuántos ceses voluntarios hubo en Enero 2025?"*

### 🟡 Intermedias (Listados y Segmentos)
1.  **Listado Detallado**: *"Dame la lista de colaboradores cesados en Q1 2025."*
2.  **Filtro Compuesto**: *"¿Quiénes son los HiPo que renunciaron en 2025?"*
3.  **Comparativa Simple**: *"Comparar rotación entre Fuerza de Ventas y Administrativos."*

### 🔴 Avanzadas (Tendencias y Análisis Crítico)
1.  **Tendencia Temporal**: *"Grafica la evolución mensual de la rotación voluntaria en el último año."*
2.  **Reporte Ejecutivo (Full Context)**: *"Genera el reporte ejecutivo de Marzo 2025."* (Inyecta datos en IA para análisis de causas).
3.  **Comparativa Multidimensional**: *"Muéstrame la rotación por División ordenado de mayor a menor."*
