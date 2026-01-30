# Especificación Funcional (HU-006)

## Definición de la Funcionalidad
Herramienta de análisis que agrupa los datos de ceses (Leavers) según una dimensión solicitada por el usuario, retornando una estructura optimizada para gráficos.

## Parámetros de Entrada (Input)
El usuario puede solicitar agrupar por:
1.  **"División"** (`breakdown_by=UO2`): Para ver impacto macro.
2.  **"Área"** (`breakdown_by=UO3`): Para ver focos específicos.
3.  **"Motivo"** (`breakdown_by=MOTIVO`): Para entender causas (Renuncia vs Despido).
4.  **"Posición"** (`breakdown_by=POSICION`): Para ver roles afectados.
5.  **"Antigüedad"** (`breakdown_by=TENENCIA`): *Nice to have* (Rango de años).

*Nota: Debe respetar los mismos filtros que `get_leavers_list` (Periodo, Segmento, Tipo de Rotación).*

## Salida Esperada (Output)
Un objeto JSON estandarizado `VisualDataPackage` con:
*   `type`: "bar_chart" | "pie_chart".
*   `data`: Lista de `{ label: "Nombre Categ", value: 12, percentage: 0.15 }`.
*   `title`: Título autogenerado (ej. "Distribución de Ceses por Área - 2024").

## Comportamiento del Agente
*   Si el usuario dice "Grafícalo", el Agente debe inferir la dimensión más lógica (usualmente Área o Motivo) o preguntar.
*   Si el resultado tiene demasiadas categorías (ej. > 20 áreas), el Backend debe agrupar las menores en "Otros" para no romper el gráfico.
