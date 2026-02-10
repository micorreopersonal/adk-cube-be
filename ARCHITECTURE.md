# 📊 Arquitectura del Asistente de People Analytics (Backend)

## 🎯 Visión General

El **ADK People Analytics Backend** es un sistema de análisis conversacional basado en arquitectura de agentes que transforma consultas en lenguaje natural en análisis de datos de RRHH precisos y visuales, utilizando el patrón **Semantic Cube** para separar la capa de inteligencia (probabilística/LLM) de la capa de datos (determinística/SQL).

---

## 🏗️ Patrón Arquitectónico: "Semantic Cube"

### Principio Fundamental
**Separación estricta entre lógica probabilística (IA) y lógica determinística (Datos)**

```
┌─────────────────────────────────────────────────────┐
│  CAPA PROBABILÍSTICA (AI)                           │
│  - Interpretación de lenguaje natural               │
│  - Generación de narrativas/insights                │
│  - Enrutamiento de intenciones                      │
└─────────────────────────────────────────────────────┘
                       ↕️ (Interfaz Semántica)
┌─────────────────────────────────────────────────────┐
│  CAPA DETERMINÍSTICA (Semantic Engine)              │
│  - Registry de métricas (Single Source of Truth)    │
│  - Generación SQL segura (anti-SQL injection)       │
│  - Validación de dimensiones y filtros              │
│  - Visualización automática                         │
└─────────────────────────────────────────────────────┘
                       ↕️
┌─────────────────────────────────────────────────────┐
│  CAPA DE DATOS (BigQuery)                           │
│  - Data Warehouse                                   │
│  - Tablas de hechos (rotación, headcount)           │
└─────────────────────────────────────────────────────┘
```

---

## 📁 Estructura de Directorios (Semantic Cube)

```
app/
├── ai/                     # [CEREBRO] - Capa de Inteligencia
│   ├── agents/             # Lógica de Orquestación
│   │   ├── router_logic.py      # Router Agent (enrutamiento de consultas)
│   │   └── hr_agent_persona.py  # HR Agent (respuestas conversacionales)
│   │
│   └── tools/              # Herramientas Especializadas
│       ├── universal_analyst.py        # Motor Semántico Principal
│       ├── executive_report_orchestrator.py  # Reportes Ejecutivos
│       └── executive_insights.py       # Generador de Narrativas AI
│
├── core/                   # [DEFINICIONES] - Lógica de Negocio
│   ├── analytics/
│   │   └── registry.py     # ⭐ REGISTRY (Single Source of Truth)
│   ├── config.py           # Configuración (Pydantic Settings)
│   └── security.py         # RBAC y Autenticación
│
├── services/               # [MÚSCULO] - Ejecución
│   ├── query_generator.py       # Motor SQL Seguro
│   ├── bigquery.py              # Cliente BigQuery (Singleton)
│   └── adk_firestore_connector.py  # Sesiones (Stateless)
│
└── api/                    # [INTERFAZ] - Endpoints
    └── main.py             # FastAPI Entrypoint
```

---

## 🧠 Componentes Clave

### 1. **Registry (Single Source of Truth)**
**Ubicación:** `app/core/analytics/registry.py`

**Propósito:** Definición centralizada de todas las métricas y dimensiones del negocio.

**Ejemplo:**
```python
METRIC_DEFINITIONS = {
    "tasa_rotacion": {
        "sql_expression": """
            SAFE_DIVIDE(
                COUNT(DISTINCT CASE WHEN estado = 'Cesado' THEN codigo_persona END),
                COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END)
            ) * 100
        """,
        "display_name": "Tasa de Rotación (%)",
        "format": "percentage"
    },
    "ceses_totales": {...},
    "headcount_promedio": {...}
}

DIMENSION_DEFINITIONS = {
    "uo2": {"column": "uo2", "display": "División"},
    "grupo_segmento": {"column": "segmento", "display": "Segmento"},
    "genero": {...}
}
```

**Fortaleza:** 
- ✅ **Consistencia:** La misma métrica se calcula igual en dashboards, reportes y queries conversacionales
- ✅ **Mantenibilidad:** Cambiar una definición actualiza todo el sistema
- ✅ **Validación:** Impide que el LLM invente métricas inexistentes

---

### 2. **Universal Analyst (Motor Semántico)**
**Ubicación:** `app/ai/tools/universal_analyst.py`

**Función:** Traduce consultas semánticas en SQL seguro y genera visualizaciones automáticas.

**Flujo:**
```
execute_semantic_query(intent, cube_query, metadata)
    ↓
1. Validar métricas/dimensiones contra Registry
2. Llamar a query_generator.build_analytical_query()
3. Ejecutar SQL en BigQuery
4. Procesar resultados → VisualBlock
    - SNAPSHOT → KPI Row
    - COMPARISON → Bar Chart
    - TREND → Line Chart
    - LISTING → Table
5. Retornar VisualDataPackage
```

**Anti-Patrón Prevenido:**
```python
# ❌ NO SE HACE ESTO (riesgo de alucinación)
sql = llm.generate(f"Genera SQL para: {user_query}")
bigquery.execute(sql)

# ✅ SE HACE ESTO (seguro y validado)
cube_query = {"metrics": ["tasa_rotacion"], "filters": [...]}
result = execute_semantic_query("SNAPSHOT", cube_query)
```

---

### 3. **Router Agent (Enrutamiento Inteligente)**
**Ubicación:** `app/ai/agents/router_logic.py`

**Propósito:** Clasificar la intención del usuario y enrutar a la herramienta correcta.

**Rutas:**
1. **Análisis Ad-Hoc** → `universal_analyst`
2. **Reporte Ejecutivo** → `executive_report_orchestrator`
3. **Chat General** → Respuesta directa del LLM

**Prompt Engineering:**
```python
"""
Eres un router inteligente. Clasifica la consulta:
- Si pide datos específicos → "analytical_query"
- Si pide reporte ejecutivo → "executive_report"
- Si es conversacional → "general_chat"
"""
```

---

### 4. **Executive Report Orchestrator**
**Ubicación:** `app/ai/tools/executive_report_orchestrator.py`

**Características:**
- ✅ Genera reportes multi-sección (Headlines, Segmentación, Voluntaria, Talento, Tendencia)
- ✅ Usa **100% el motor semántico** (7-8 queries estructuradas)
- ✅ AI Context-Aware: Extrae datos de gráficos/tablas y los envía al LLM para insights
- ✅ Flexible: Soporta YYYY, YYYYQN, YYYYMM, YYYYMM-YYYYMM
- ✅ Modular: Puede generar secciones específicas para testing

**Ejemplo de Query Sequence:**
```python
[
    {"section": "headline_current", "intent": "SNAPSHOT", "metrics": [...]},
    {"section": "segmentation", "intent": "COMPARISON", "dimensions": ["grupo_segmento"]},
    {"section": "talent_leakage", "intent": "LISTING", "filters": [{"dimension": "talento", "value": ["HiPo"]}]}
]
```

---

### 5. **Query Generator (Motor SQL)**
**Ubicación:** `app/services/query_generator.py`

**Responsabilidad:** Construir SQL válido desde objetos estructurados.

**Proceso:**
```python
def build_analytical_query(metrics, dimensions, filters):
    # 1. Validar contra Registry
    for m in metrics:
        assert m in METRIC_DEFINITIONS
    
    # 2. Construir SELECT
    select_clause = [METRIC_DEFINITIONS[m]["sql_expression"] for m in metrics]
    
    # 3. Construir WHERE (sanitizado)
    where_clause = build_where_clause(filters)  # Usa placeholders, no concatenación
    
    # 4. Retornar SQL seguro
    return f"SELECT {select_clause} FROM {TABLE} WHERE {where_clause}"
```

**Anti-SQL Injection:**
- ✅ No hay interpolación de strings del usuario
- ✅ Filtros validados contra dimensiones permitidas
- ✅ Valores sanitizados

---

## 🔐 Seguridad y Gobernanza

### RBAC (Role-Based Access Control)
**Ubicación:** `app/core/security.py`

```python
ROLE_PERMISSIONS = {
    "analyst": ["view_metrics", "export_data"],
    "admin": ["view_metrics", "export_data", "manage_users"],
    "viewer": ["view_metrics"]
}
```

### Stateless Architecture
- **Sesiones en Firestore:** No se guarda estado en memoria del contenedor
- **Beneficio:** Escalabilidad horizontal en Cloud Run

---

## 📊 Flujo Completo de una Consulta

### Ejemplo: "¿Cuál es la rotación de VENTAS en enero 2025?"

```
1. USER → FastAPI Endpoint
   POST /api/chat {"message": "¿Cuál es la rotación de VENTAS en enero 2025?"}
   
2. Router Agent (LLM)
   Clasificación → "analytical_query"
   Parámetros extraídos:
     - metrics: ["tasa_rotacion"]
     - filters: [{"dimension": "uo2", "value": "VENTAS"}, 
                 {"dimension": "periodo", "value": "202501"}]
   
3. Universal Analyst
   ├─ Validar "tasa_rotacion" existe en Registry ✅
   ├─ Validar "uo2" es dimensión válida ✅
   └─ Llamar a Query Generator
   
4. Query Generator
   SQL generado:
     SELECT 
       SAFE_DIVIDE(
         COUNT(DISTINCT CASE WHEN estado = 'Cesado' THEN codigo_persona END),
         COUNT(DISTINCT CASE WHEN estado = 'Activo' THEN codigo_persona END)
       ) * 100 AS tasa_rotacion
     FROM hr_analytics.fact_hr_rotation
     WHERE uo2 = 'VENTAS' AND FORMAT_DATE('%Y%m', periodo) = '202501'
   
5. BigQuery Client (Singleton)
   Ejecutar SQL → Retornar resultados
   
6. Universal Analyst (Visualización)
   Intent = SNAPSHOT → Generar KPIBlock
   {
     "type": "KPI_ROW",
     "payload": {
       "items": [{"label": "Tasa de Rotación", "value": 5.2, "format": "percentage"}]
     }
   }
   
7. HR Agent (Narrativa)
   LLM genera respuesta:
   "En enero 2025, la división de VENTAS tuvo una tasa de rotación del 5.2%, 
    lo cual representa un incremento de 0.8 pts respecto a diciembre 2024."
   
8. FastAPI → USER
   Retorna VisualDataPackage (JSON) con KPI + Narrativa
```

---

## 💪 Fortalezas Clave

### 1. **Anti-Alucinación**
- ❌ El LLM **NO** genera SQL directamente
- ✅ El LLM solo extrae parámetros estructurados
- ✅ El Registry valida que las métricas existen

### 2. **Mantenibilidad**
- ✅ Single Source of Truth (Registry)
- ✅ Cambiar una métrica actualiza todo el sistema
- ✅ Código modular y testeado

### 3. **Escalabilidad**
- ✅ Stateless (sesiones en Firestore)
- ✅ BigQuery Client Singleton (reutiliza conexiones)
- ✅ Cloud Run auto-scaling

### 4. **Trazabilidad**
- ✅ Logs estructurados en cada capa
- ✅ Telemetría de tiempos (Prep, SQL Gen, BQ Exec, Viz)
- ✅ Context logs para debugging de AI (`🤖 [CTX]`)

### 5. **Flexibilidad**
- ✅ Soporta análisis ad-hoc y reportes estructurados
- ✅ Múltiples formatos temporales (YYYY, YYYYQN, YYYYMM, rangos)
- ✅ Filtros organizacionales (UO2, segmento, género, etc.)

---

## 🧪 Testing y Validación

### Test Pyramid
```
┌────────────────────┐
│ Integration Tests  │  ← Reporte ejecutivo end-to-end
├────────────────────┤
│   Unit Tests       │  ← Query Generator, Registry validations
├────────────────────┤
│ Regression Tests   │  ← test_semantic_core.py (Suite crítica)
└────────────────────┘
```

### Herramientas de Validación
- `tests/test_semantic_core.py`: Suite de regresión para métricas críticas
- `tests/validate_sections.py`: Validación sección por sección de reportes
- `tests/verify_report_context_validation.py`: Criterios de aceptación de contexto AI

---

## 🚀 Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| **Framework** | FastAPI (Python 3.11+) |
| **LLM** | Google Gemini (Vertex AI) |
| **Data Warehouse** | BigQuery |
| **State Management** | Firestore |
| **Deployment** | Cloud Run (GCP) |
| **Validation** | Pydantic |
| **Testing** | pytest |

---

## 📈 Métricas del Sistema

- **Líneas de Código:** ~3,500 (backend core)
- **Métricas en Registry:** 15+ definidas
- **Dimensiones soportadas:** 12+ (UO2, segmento, género, tipo_contrato, etc.)
- **Queries del Reporte Ejecutivo:** 7-8 queries estructuradas
- **Tiempo promedio de respuesta:** <5s para queries simples, <15s para reportes ejecutivos

---

## 🎯 Casos de Uso Actuales

1. **Análisis Ad-Hoc Conversacional**
   - "¿Cuántos HiPos renunciaron en IT este trimestre?"
   - "Muéstrame la rotación voluntaria por género en 2024"

2. **Reportes Ejecutivos Automatizados**
   - Reporte mensual de rotación con insights de AI
   - Alertas de fuga de talento clave

3. **Análisis Comparativo**
   - Rotación ADMIN vs FFVV
   - Tendencias año sobre año (YoY)

---

## 📚 Documentación Adicional

- [`docs/CAPABILITIES.md`](./docs/CAPABILITIES.md) - Resumen de capacidades técnicas
- [`docs/EXECUTIVE_REPORT_FILTERS.md`](./docs/EXECUTIVE_REPORT_FILTERS.md) - Guía de filtros del reporte ejecutivo
- [`docs/GLOBAL_RULES.md`](./docs/GLOBAL_RULES.md) - Reglas de gobernanza y desarrollo

---

**Conclusión:** El backend de ADK People Analytics implementa una arquitectura robusta basada en el patrón Semantic Cube, donde la separación entre lógica probabilística (LLM) y lógica determinística (Datos) garantiza precisión, mantenibilidad y escalabilidad para análisis de RRHH de nivel empresarial.
