# Métricas de Calidad de IA (Observabilidad)

## KPIs de Calidad
1. **Tasa de Alucinación Numérica:**
   - **Definición:** Respuestas donde el número entregado no coincide con el dato en BQ.
   - **Meta:** 0%. (Hard Constraint)
   
2. **Adherencia a Formato Markdown:**
   - **Definición:** % de respuestas que respetan la estructura de reporte solicitada (Insight, Segmentación, Alerta).
   - **Meta:** 95%.

3. **Latencia E2E:**
   - **Meta:** < 5 segundos para respuestas simples, < 15 segundos para reportes complejos.

4. **Densidad de Peticiones (Quotas):**
   - **Métrica:** Promedio de Model Turns por consulta.
   - **Meta:** < 3 turns (Optimización de logic/herramientas). 
   - **Monitor:** Registro de errores 429 para identificar saturación de RPM.

4. **Consumo de Cuota (Profiling):**
   - **Métrica:** Promedio de Model Turns por Consulta.
   - **Definición:** Número de llamadas a la API de IA necesarias para resolver una duda.
   - **Meta:** < 2.5 turnos promedio.
