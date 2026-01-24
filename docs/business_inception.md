# BLUEPRINT DE CONFIGURACIÓN: AGENTE DE IA - HR ANALYTICS

Este documento constituye la "Fuente de Verdad" (SSoT) para el desarrollo de la solución multi-agéntica con ADK de Google. Define la lógica, el lenguaje organizacional y las restricciones operativas del sistema.

## 1. MAPA DE ESTRUCTURA ORGANIZACIONAL (DIMENSIONES)
El agente debe mapear las columnas de BigQuery a los siguientes términos de negocio:
* uo2: División.
* uo3: Área.
* uo4: Gerencia.
* uo5: Equipos / Canales (Ej: Canal VIP, Canales Digitales, Convenios).
* uo6: Equipos Nivel 2.

## 2. GLOSARIO Y REGLAS DE NEGOCIO (BUSINESS LOGIC)
* Exclusión de Practicantes: El segmento "PRACTICANTE" debe excluirse de todos los cálculos de rotación y dotación profesional.
* Criterio de Voluntariedad: Un cese es "Voluntario" únicamente si el campo 'motivo_cese' contiene la palabra "RENUNCIA".
* Segmentación Core:
    * FFVV: Colaboradores con campo 'segmento' = "EMPLEADO FFVV".
    * ADMI: Colaboradores con campo 'segmento' ≠ "EMPLEADO FFVV" (y ≠ "PRACTICANTE").
* Jerarquía de Liderazgo (Jefe+): Filtrar por campo 'segmento' que incluya: "JEFE", "SUB-GERENTE", "GERENTE" y "GERENTE CORPORATIVO".

## 3. INTEGRIDAD DE DATOS (REGLA DE ORO)
* Cero Alucinaciones Numéricas: El LLM no debe realizar cálculos matemáticos. Todos los números, ratios y variaciones deben ser calculados mediante Tools (SQL en BigQuery).
* Rol del LLM: El modelo se encarga exclusivamente de la síntesis analítica, interpretación de resultados y redacción de conclusiones estratégicas basadas en los datos calculados.

## 4. FÓRMULAS DE INDICADORES (MÉTRICAS)
* Rotación Mensual: (Suma de Cesados del Mes / Headcount Inicial del Mes).
* Headcount Inicial: Es el saldo de personal al cierre del mes inmediatamente anterior.
* Proyectado Anual: (Acumulado Año Actual / Meses Transcurridos) * 12.
* Talento Clave: 
    * Hipers: Valor 7 en campo 'mapeo_talento_ultimo_anio'.
    * Hipos: Valores 8 y 9 en campo 'mapeo_talento_ultimo_anio'.

## 5. ESTRUCTURA DEL "BOLETÍN MENSUAL DE HR INSIGHTS"
El agente debe generar los reportes con los siguientes componentes en Markdown:
1. Insight Crítico: Análisis narrativo de la variación del mes vs. el promedio del año.
2. Segmentación: Comparativa de ratios entre ADMI y FFVV.
3. Tendencia YTD: Visualización en texto de la evolución de la rotación voluntaria mensual.
4. Focos de Concentración: Identificación de las Divisiones (uo2) o Áreas (uo3) con mayor rotación.
5. Alerta de Talento: Tabla con detalle (Nombre, Posición, Motivo) de ceses de Hipers e Hipos.
6. Tabla Comparativa: Mes Actual vs. Promedio Anual (Total Cesados, % Rotación Voluntaria, % Rotación General).
7. Conclusión Estratégica y Recomendaciones: Análisis de causa raíz y planes de acción sugeridos para retención.