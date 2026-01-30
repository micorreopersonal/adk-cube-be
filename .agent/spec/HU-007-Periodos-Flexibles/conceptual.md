# HU-007: Periodos Flexibles en Análisis de Tendencias

## 1. El Problema
Actualmente, la herramienta `get_monthly_trend` es rígida: siempre devuelve la serie completa de Enero a Diciembre del año solicitado.
*   **Caso de Uso:** Usuario pide "Analiza la tendencia de rotación del último trimestre (Oct-Dic)".
*   **Resultado Actual:** El sistema muestra gráficos de Ene-Dic, lo cual añade ruido visual y diluye el foco del análisis.

## 2. La Solución
Refactorizar `get_monthly_trend` para aceptar parámetros opcionales de rango.

### Cambios Propuestos:
1.  **Backend:**
    *   Nuevo parámetro: `month_start` (int, default=1).
    *   Nuevo parámetro: `month_end` (int, default=12).
    *   Lógica SQL/Pandas: Filtrar los resultados para incluir solo los meses en el rango `[month_start, month_end]`.

2.  **Agente (Prompt):**
    *   Instruir al agente para detectar rangos: "último trimestre" -> `start=10, end=12`. "segundo semestre" -> `start=7, end=12`.

## 3. Valor para el Negocio
Permite análisis más quirúrgicos ("Zoom-in") en periodos críticos, eliminando la distracción de meses irrelevantes.
