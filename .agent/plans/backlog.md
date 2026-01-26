# PRODUCT BACKLOG: HR ANALYTICS AI AGENT

## FEATURE 1: BOLETÍN MENSUAL DE HR INSIGHTS (CORE)
**Descripción:** Orquestación automática de consultas para generar una narrativa estratégica del cierre de mes, integrando métricas pasadas, presentes y desviaciones.

### US-1.1: Generación del Boletín Estratégico (Snapshot 360°)
> **Como** Líder de Talento,
> **Quiero** solicitar un "Reporte de ceses de [Mes] [Año]",
> **Para** obtener una visión holística del impacto de la rotación sin tener que consultar múltiples dashboards.

**Criterios de Aceptación:**
1.  [cite_start]**Estructura:** El output debe seguir estrictamente los 7 puntos definidos en el Blueprint (Insight, Segmentación, Tendencia, Focos, Talento, Tabla, Conclusiones)[cite: 1257].
2.  **Integridad de Cálculo:** El Agente debe invocar la tool `get_monthly_metrics` que calcula:
    * Total Cesados (excluyendo 'PRACTICANTE').
    * % Rotación Voluntaria (filtro 'RENUNCIA' / HC Inicial Mes).
    * [cite_start]% Rotación General (Total Cesados / HC Inicial Mes)[cite: 1257].
3.  **Comparativa:** Debe mostrar automáticamente la variación del mes actual vs. el promedio del año en curso.

### US-1.2: Visualización de Tendencia YTD (Sparklines)
> **Como** Usuario de Negocio,
> **Quiero** visualizar la evolución mes a mes de la rotación voluntaria en el mismo chat,
> **Para** identificar rápidamente si la tendencia es ascendente o descendente sin abrir gráficos externos.

**Criterios de Aceptación:**
1.  **Formato:** Renderizar gráfico de barras utilizando caracteres de texto (Ej: ▂▃▅▆) o lista Markdown clara.
2.  **Alcance:** Mostrar datos desde Enero hasta el mes actual del año fiscal seleccionado.

---

## FEATURE 2: ANÁLISIS MULTIDIMENSIONAL & DRILL-DOWN
**Descripción:** Capacidad del agente para "cortar" los datos por las dimensiones organizacionales y demográficas definidas en el esquema.

### US-2.1: Segmentación Binaria (ADMI vs FFVV)
> **Como** HRBP,
> **Quiero** ver los indicadores separados por fuerza de ventas y administrativos,
> **Para** aplicar estrategias de retención diferenciadas.

**Criterios de Aceptación:**
1.  [cite_start]**Filtro FFVV:** `segmento` = 'EMPLEADO FFVV'[cite: 1257].
2.  [cite_start]**Filtro ADMI:** `segmento` ≠ 'EMPLEADO FFVV' AND `segmento` ≠ 'PRACTICANTE'[cite: 1257].
3.  **Output:** El reporte debe presentar los KPIs de ambos grupos lado a lado.

### US-2.2: Navegación Jerárquica (Drill-down Organizacional)
> **Como** Gerente de División,
> **Quiero** profundizar desde mi División (UO2) hasta mis Áreas (UO3) y Gerencias (UO4),
> **Para** detectar exactamente dónde se originan los focos de rotación.

**Criterios de Aceptación:**
1.  [cite_start]**Mapeo:** El agente debe reconocer: División -> `uo2`, Área -> `uo3`, Gerencia -> `uo4`[cite: 106].
2.  **Lógica Relacional:** Si el usuario pregunta por una División específica, el agente debe listar las Áreas (uo3) dentro de esa División que superan el promedio de rotación.

### US-2.3: Análisis por Canales de Venta (UO5)
> **Como** Líder Comercial,
> **Quiero** analizar la rotación por canales específicos (VIP, Digital, Tienda, Convenios),
> **Para** entender la dinámica operativa de cada frente de ventas.

**Criterios de Aceptación:**
1.  [cite_start]**Mapeo:** Utilizar el campo `uo5` para identificar canales[cite: 568, 644, 677].
2.  **Contexto:** El agente debe ser capaz de comparar la rotación entre canales (Ej: Canal VIP vs Canal Digital).

### US-2.4: Filtro de Liderazgo (Jefe+)
> **Como** Director de RRHH,
> **Quiero** monitorear exclusivamente la rotación de posiciones de mando,
> **Para** proteger la estabilidad de la estructura de liderazgo.

**Criterios de Aceptación:**
1.  [cite_start]**Filtro Agregado:** Incluir registros donde `segmento` IN ('JEFE', 'SUB-GERENTE', 'GERENTE', 'GERENTE CORPORATIVO')[cite: 196, 198, 199, 200].
2.  **Alerta:** Cruzar siempre con métricas de desempeño/talento.

---

## FEATURE 3: MONITOR DE TALENTO CRÍTICO (HIPERS/HIPOS)
**Descripción:** Sistema de alerta temprana y reporte detallado sobre la fuga de capital humano de alto valor.

### US-3.1: Alerta de Fuga de Potencial
> **Como** Especialista de Talento,
> **Quiero** recibir una lista detallada de los Hipers e Hipos que renunciaron en el periodo,
> **Para** realizar entrevistas de salida profundas y activar planes de contingencia.

**Criterios de Aceptación:**
1.  **Clasificación:**
    * [cite_start]Hipers: `mapeo_talento_ultimo_anio` = 7[cite: 718].
    * [cite_start]Hipos: `mapeo_talento_ultimo_anio` IN (8, 9)[cite: 719].
2.  **Detalle Requerido:** Nombre, Posición, División (uo2) y Motivo de Cese.
3.  **Feedback Negativo:** Si no hubo salidas de talento, el agente debe indicarlo explícitamente ("0 fugas de talento clave este mes").

---

## FEATURE 4: MOTOR DE CÁLCULO PROYECTIVO
**Descripción:** Herramienta para estimar el cierre del año basándose en el comportamiento actual (Run Rate).

### US-4.1: Proyección de Cierre Anual
> **Como** Gerente de Planeamiento,
> **Quiero** saber cuál será la rotación anual proyectada si mantenemos la tendencia actual,
> **Para** ajustar presupuestos de reclutamiento.

**Criterios de Aceptación:**
1.  [cite_start]**Fórmula:** Aplicar `(Acumulado Año Actual / Meses Transcurridos) * 12`[cite: 1257].
2.  **Comparativa YoY:** Comparar el valor proyectado contra el Cierre Real del año anterior para indicar mejora o deterioro.