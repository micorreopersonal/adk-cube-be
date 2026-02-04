# Resumen Conceptual: Capa de Esquemas (`app/schemas`)

La carpeta `app/schemas` define el **Contrato de Datos (Data Contracts)** del sistema. Utiliza **Pydantic** para validar estrictamente las entradas y salidas, garantizando que el Agente, el Backend y el Frontend hablen el mismo idioma sin ambigüedades.

Se divide en tres dominios funcionales:

## 1. Protocolo de Entrada (`analytics.py`)
Define **cómo el Agente solicita información** al núcleo semántico. Es el "DSL" (Domain Specific Language) interno del sistema.

*   `SemanticRequest`: El sobre maestro que envuelve toda petición analítica.
*   `CubeQuery`: La estructura agnóstica de una consulta SQL (sin ser SQL). Define *Qué* métricas, *Por Qué* dimensiones y *Con Qué* filtros.
*   `FilterCondition`: Normaliza los filtros (`dimension`, `operator`, `value`) evitando inyecciones y errores de sintaxis.
*   `RequestMetadata`: Instrucciones de visualización (ej. "Quiero un gráfico de barras" o "Sugiéreme un título").

**Propósito:** Desacoplar la intención del usuario de la implementación en base de datos. El agente solo necesita llenar este formulario JSON.

## 2. Protocolo de Salida Visual (`payloads.py`)
Define **cómo el Backend responde al Frontend** para renderizar componentes ricos. Es el protocolo "Server-Driven UI".

*   `VisualDataPackage`: El paquete maestro de respuesta. Contiene un resumen textual y una lista de bloques visuales.
*   `VisualBlock`: Bloques atómicos de interfaz.
    *   `KPIBlock`: Tarjetas de indicadores (ej. "Tasa de Rotación: 15%").
    *   `ChartBlock`: Gráficos dinámicos (Líneas, Barras) agnósticos de la librería de JS (compatible con Chart.js/Recharts).
    *   `TableBlock`: Tablas de datos crudos formateados.
    *   `TextBlock`: Texto enriquecido o insights.

**Propósito:** Que el Agente no devuelva texto plano, sino experiencias de usuario completas. El Front es "tonto" (solo renderiza lo que el Back le dice).

## 3. Contrato de API (`chat.py`)
Define la **Interfaz Pública HTTP** (REST API) expuesta en `app/api/routes.py`.

*   `ChatRequest`: Lo que envía el cliente (Mensaje, ID de sesión, Perfil de usuario).
*   `ChatResponse`: Lo que devuelve el servidor (Texto + Payload Visual).
*   `Token` / `TokenData`: Estructuras de autenticación (JWT).

**Propósito:** Validar la comunicación HTTP externa y manejar la seguridad del transporte.

---

## Flujo de Datos
1.  **Frontend** envía `ChatRequest` → **API** (`chat.py`)
2.  **Agente** traduce el mensaje a `SemanticRequest` → **Universal Analyst** (`analytics.py`)
3.  **Universal Analyst** ejecuta BigQuery y empaqueta resultados en `VisualDataPackage` → **Response** (`payloads.py`)
