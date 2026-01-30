### DOCUMENTO: MAPEO DE DATOS Y UX - FRONTEND (STREAMLIT)
**Contexto:** El Frontend recibirá la respuesta de las Tools en formato JSON. Se requiere consistencia visual con el branding de RIMAC.

#### A. MAPEO DE COMPONENTES POR TOOL
1. **Para `get_turnover_deep_dive`:**
   - **Métrica Clave (`st.metric`):** Mostrar el % de Rotación actual vs el mes anterior (Delta).
   - **Gráfico de Línea (`st.line_chart`):** Eje X: Meses del periodo. Eje Y: % Rotación.
   - **Brillo (UX):** Si el valor supera el 30% anualizado, mostrar en color ámbar/rojo.

2. **Para `get_talent_leakage`:**
   - **Gráfico de Barras Horizontal:** Comparar `Cesados Voluntarios` vs `Cesados Inducidos` para los segmentos 7, 8 y 9.
   - **Tabla Detallada (`st.dataframe`):** Mostrar `Nombre`, `Posicion`, `UO2` y `Antigüedad (ts_anios)`.
   - **Brillo (UX):** Resaltar con un badge "CRÍTICO" si el colaborador cesado es un HIPOS (8 o 9).

3. **Para `predict_attrition_factors`:**
   - **Mapa de Calor o Treemap:** Tamaño del cuadro = N° de Ceses. Color = Intensidad de la tasa de rotación por Supervisor o Sede.
   - [cite_start]**Brillo (UX):** Usar `st.expander` para mostrar el "Análisis de Causa Raíz" (principales motivos de cese como 'Oportunidad Laboral' [cite: 995, 1017]).

#### B. DICCIONARIO DE COLORES Y ESTILOS
- **Primary Color:** #EF3340 (Rojo RIMAC) para alertas de alta rotación.
- **Secondary Color:** #00A3E0 (Azul) para HC Activo y estabilidad.
- **Neutral:** #F4F4F4 para fondos de tarjetas de KPI.

#### C. ESTRUCTURA DEL PAYLOAD ESPERADO (JSON EXAMPLE)
{
  "tool_name": "get_talent_leakage",
  "kpis": {
    "total_ceses": 19,
    "rotacion_anual_pct": 13.37,
    "segmento": "HIPOS (8 y 9)"
  },
  "chart_data": [
    {"mes": "Ene", "valor": 1.99},
    {"mes": "Abr", "valor": 3.38},
    ...
  ],
  "insights": "La rotación de HIPOS se concentró en Abril con un 3.38%[cite: 793, 807]."
}