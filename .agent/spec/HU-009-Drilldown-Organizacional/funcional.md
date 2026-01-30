# HU-009: Especificación Funcional

## Historia de Usuario
**Como** Gerente de Persona o HRBP,
**Quiero** pedirle al agente: "Haz un desglose de la rotación en la División Salud y dime cuáles son las áreas críticas",
**Para** activar planes de acción específicos en las unidades con mayor riesgo.

## Criterios de Aceptación
1.  **Detección de Jerarquía:** El agente debe detectar si el usuario pregunta por una División (UO2) para sugerir un desglose por Áreas (UO3).
2.  **Benchmark Automático:** El sistema debe calcular la tasa de rotación promedio de la unidad padre (Benchmark).
3.  **Identificación de Hotspots:** Se deben resaltar explícitamente las sub-unidades que superen el Benchmark.
4.  **Visualización:** El output debe incluir:
    *   Insight ejecutivo con el diagnóstico.
    *   Gráfico de comparación (Sub-unidades vs. Promedio Padre).
    *   Listado de las top unidades críticas.

## Flujo del Usuario
1.  Usuario: "¿Cuál es el área más crítica de la División Finanzas?"
2.  Agente: Analiza UO2="FINANZAS", calcula promedio, compara contra todas las UO3 contenidas.
3.  Respuesta: "La División Finanzas tiene una rotación del 12%. Sin embargo, el **Área de Contabilidad** es un hotspot crítico con 25%."
