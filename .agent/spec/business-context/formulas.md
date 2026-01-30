# PRODUCT BACKLOG: HR ANALYTICS REVENUE & RETENTION TOOLS
# Versión: 2.1 | Fecha: 26/01/2026
# Insumo para: Equipo de Desarrollo Antigravity

---

### 1. CORE METRICS (Fórmulas Base)
Estas métricas deben ser calculadas dinámicamente sobre la tabla de BigQuery.

- **Personal Activo (Headcount):**
  COUNT(DISTINCT codigo_persona) WHERE estado = "Activo"

- **Personal Cesado (Bajas):**
  COUNT(DISTINCT codigo_persona) WHERE estado = "Cesado"

- **Saldo Inicial (Antes del Mes):**
  Corresponde al Headcount del periodo anterior (t-1).
  En DAX: CALCULATE([Personal Activo], PARALLELPERIOD(periodo, -1, MONTH))

- **Cese Voluntario (Filtro Estricto):**
  COUNT(DISTINCT codigo_persona) WHERE estado = "Cesado" AND motivo_cese = "RENUNCIA"

---

### 2. TURNOVER KPIs (Métricas de Rotación)
Lógica de cálculo porcentual según requerimientos de negocio.

- **% Rotación Mensual:**
  (Suma de Cesados del Mes / Headcount Inicial del Mes) * 100

- **% Rotación Total Anualizada (OFICIAL):**
  DIVIDE(Total Cesados Año, Promedio Headcount Anualizado, 0)
  *Nota: El denominador "OFICIAL" usa el promedio de dotación de los 12 meses o acumulados.*

- **% Rotación Voluntaria:**
  (Total Cesados por RENUNCIA / Headcount Inicial del Mes) * 100

- **Proyectado Acumulado a Fin de Año:**
  (Acumulado Año Actual / Número de Meses Transcurridos) * 12

---

### 3. SEGMENTACIÓN Y DIMENSIONES (Slicing)
El Agente debe ser capaz de filtrar estas métricas por las siguientes dimensiones clave:

- **Segmento FFVV (Prioritario):** Filtro: segmento = "EMPLEADO FFVV". 
  Si el usuario pregunta por "Ventas", "Fuerza de Ventas" o "Canal", priorizar esta lógica.
  
- **Diversidad Generacional:**
  Dimensiones: "Millennials", "Generación X", "Generación Z", "Generación Alfa", "Baby Boomers".

- **Niveles de Talento (Mapping):**
  - HIPERS: mapeo_talento_ultimo_anio = 7
  - HIPOS: mapeo_talento_ultimo_anio IN (8, 9)
  - TALENTOS: mapeo_talento_ultimo_anio IN (7,8,9)

---

### 4. REGLAS DE NEGOCIO (Gema AI Guardrails)
1. **Definición de Voluntaria:** Solo se considera voluntaria si el campo `motivo_cese` es estrictamente "RENUNCIA".
2. **Denominadores:** Para reportes anuales, el denominador debe ser el promedio de dotación (HC Promedio), no el cierre de un solo mes.
3. **Exclusiones:** En reportes de "Rotación ADM + FFVV", excluir siempre el segmento "PRACTICANTE" a menos que se solicite explícitamente.