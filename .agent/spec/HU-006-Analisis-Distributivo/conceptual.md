# HU-006: Análisis Distributivo y Visualización (Histogramas)

## 1. Visión del Producto
**Como:** Analista de HR / Business Partner.
**Quiero:** Poder visualizar gráficamente ("Grafícame esto por Área") la distribución de una lista de colaboradores cesados.
**Para:** Identificar patrones de fuga rápidamente (ej. "El 80% de las renuncias son de Tecnología") sin tener que contar filas manualmente en una tabla de 500 registros.

---

## 2. El Problema (Contexto)
Actualmente, el Agente entrega listas detalladas (`get_leavers_list`).
*   **Dolor:** Si la lista tiene 149 personas (como en el caso reportado), es imposible para el humano detectar qué área está más afectada solo mirando la tabla.
*   **Limitación:** El Agente no puede leer las 149 filas de su "memoria" para graficar, porque:
    1.  Costo de tokens (contexto limitado).
    2.  Riesgo de alucinación al contar.

---

## 3. La Solución Propuesta (Arquitectura)
Implementar una **Nueva Tool de Agregación** en el Backend (`get_leavers_distribution`).

### Flujo de Interacción:
1.  **Usuario:** "Muestrame los ceses de Transformación de este año."
    *   *System:* Muestra tabla (Tool: `get_leavers_list`).
2.  **Usuario:** "**Grafícalo por Área**" (o por Motivo, o Posición).
    *   *System:* Detecta intención de visualización.
    *   *AI:* Llama a `get_leavers_distribution(breakdown_by="AREA", ...filtros previos...)`.
    *   *Backend:* Ejecuta SQL: `SELECT area, COUNT(*) FROM ... GROUP BY area`.
    *   *Frontend:* Recibe JSON estandarizado `{label: "Sistemas", value: 45}` y renderiza **Gráfico de Barras**.

---

## 4. Alcance Inicial (MVP)
*   **Dimensiones de Agrupación (Eje X):**
    *   Área (`uo3`).
    *   División (`uo2`).
    *   Motivo de Cese (`motivo_cese`).
    *   Posición (`posicion`).
    *   Género/Segmento.
*   **Tipos de Gráfico:** Barras (Bar Chart) y Torta (Donut/Pie).
