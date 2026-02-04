# Prompt / Especificación para Frontend Developer (Integration Update)

**Objetivo:** Habilitar visualización agnóstica de Gráficos de Torta (`PIE_CHART`).

## Filosofía: "Blind Rendering" (Renderizado Ciego)
Para garantizar escalabilidad al 100%, el Frontend **NO debe contener lógica de negocio**.
*   **Backend:** Decide si es "Comparativa de Métricas" o "Distribución por Área". Transpone y formatea los datos.
*   **Frontend:** Solo pinta `labels` vs `datasets[0].data`. **No calcula porcentajes ni agrupa.**

---

## Contrato de Datos Universal (JSON Payload)

El Frontend recibirá siempre esta estructura estándar (Chart.js compatible), sin importar la complejidad de la consulta original.

### Caso 1: Comparativa de Métricas (Tu caso actual)
*"Ceses Voluntarios vs Involuntarios"*
El backend transpone las columnas a filas.
```json
{
  "subtype": "PIE",
  "payload": {
    "labels": ["Renuncia Voluntaria", "Despido / Destitución"],
    "datasets": [
      {
        "data": [15, 5],
        "label": "Distribución" // Etiqueta genérica para el tooltip
      }
    ]
  }
}
```

### Caso 2: Distribución Dimensional (Futuro)
*"Headcount por División"*
El backend usa los valores de la dimensión como labels.
```json
{
  "subtype": "PIE",
  "payload": {
    "labels": ["Tecnología", "RRHH", "Finanzas"],
    "datasets": [
      {
        "data": [120, 15, 40],
        "label": "Distribución"
      }
    ]
  }
}
```

## Instrucciones para el Desarrollador (Prompt AI)

> "Actúa como Senior Frontend Engineer.
> Implementa el soporte para `subtype: 'PIE'` en `ChartComponent`.
>
> **Reglas de Oro:**
> 1. **Agnosticismo:** Tu componente no sabe si muestra divisiones o tipos de baja. Solo itera `payload.labels` y `payload.datasets[0].data`.
> 2. **Tooltip Universal:** Muestra `${label}: ${value} ({percentage}%)`. Calcula el porcentaje visualmente sumando el total del dataset actual.
> 3. **Paleta:** Usa colores del Design System cíclicamente (ej. `[Color1, Color2, Color3...]`) para cada índice de `data`. No harcodees colores por nombre de label."
