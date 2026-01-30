# Especificación Funcional (HU-007)

## Definición
Mejora a la herramienta de "Tendencia Mensual" que permite al usuario definir un rango específico de meses para el análisis, evitando la carga visual de ver el año completo cuando solo interesa un periodo acotado.

## Nuevos Parámetros
*   **`month_start`** (int, Opcional): Mes de inicio (1-12). Default: 1.
*   **`month_end`** (int, Opcional): Mes de fin (1-12). Default: 12.

## Escenarios de Uso
1.  **"Tendencia del primer trimestre"**: `start=1, end=3`.
    *   *Output:* Gráfico y Tabla con solo Ene, Feb, Mar.
2.  **"Evolución desde Octubre"**: `start=10, end=12`.
    *   *Output:* Gráfico y Tabla con Oct, Nov, Dic.
3.  **"Tendencia 2025"** (Sin especificar): `start=1, end=12`.
    *   *Output:* Comportamiento estándar (año completo).

## Validación
*   Si `start > end`, el sistema debe corregirlo o lanzar error amigable.
*   Si no hay datos en el rango seleccionado, debe indicarlo claramente.
