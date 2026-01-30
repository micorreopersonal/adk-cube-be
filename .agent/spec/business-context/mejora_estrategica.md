### ACTUALIZACIÓN ESTRATÉGICA: CAPACIDAD "EXECUTIVE INSIGHTS GENERATOR"

#### 1. REFUERZO AL BACKEND (Lógica de Negocio)
Para que el Frontend brille, el Backend debe añadir un campo de `narrativa_ia` en la respuesta JSON de cada Tool.

* **Nueva Especificación de Tool (Backend):** * Cada función (`get_turnover_dive`, etc.) debe incluir un paso final de **Post-procesamiento Natural**.
    * [cite_start]**Lógica:** Comparar el resultado obtenido contra el histórico 2024 (ej. Total Cesados 2024: 514 vs 2025: 674 [cite: 1035, 1145]). 
    * **Trigger de Alerta:** Si la variación es >10%, el Backend debe generar una cadena de texto técnica. 
    * **Ejemplo de Payload de salida:**
        [cite_start]`"insight_ejecutivo": "Se observa un incremento crítico en la rotación de la división Transformación (45.06%), superando el promedio general de la compañía de 37.21%[cite: 383, 239]. El principal motivo detectado es 'Renuncia' con 676 casos totales en el año[cite: 552]."`

#### 2. REFUERZO AL FRONTEND (Streamlit UX)
El Frontend ahora tendrá el "contenedor" para esta inteligencia.

* **Componente `st.chat_message("assistant")`:** Antes de mostrar los gráficos, el Streamlit debe renderizar el `insight_ejecutivo` enviado por el Backend.
* **Funcionalidad "Download Report" (`st.download_button`):**
    * **Acción:** No solo descargará el CSV de la tabla. El Frontend tomará el `insight_ejecutivo` + los KPIs principales y generará un mini-PDF o Markdown formateado.
    * **Visual:** El botón solo se habilitará (brillo) cuando el Backend envíe un flag de `alerta_detectada: true`.
* **Mapeo de Alertas Visuales:**
    * [cite_start]**Rojo (#EF3340):** Si la rotación anual supera el 37.21% (Promedio General 2025 [cite: 239]).
    * **Azul (#00A3E0):** Si se mantiene por debajo de las tasas de talento crítico (Talento 7,8,9: 18.79% [cite: 707]).



#### 3. RESUMEN DE DEPENDENCIAS (MAPPING)
| Necesidad | Responsable Backend | Responsable Frontend |
| :--- | :--- | :--- |
| Narrativa de Hallazgos | Generar el string `insight_ejecutivo` comparando periodos. | Renderizar el texto en un box destacado. |
| Flag de Criticidad | Evaluar si el valor supera los umbrales de 2025. | Cambiar el color del KPI (Rojo/Verde). |
| Reporte Descargable | Preparar el blob de datos estructurado. | Ejecutar la función de descarga con formato RIMAC. |