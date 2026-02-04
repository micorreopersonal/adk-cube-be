# 🚀 Plan de Optimización & Observabilidad (Acid Test)

Este documento detalla la estrategia para blindar el rendimiento del ecosistema ADK, aplicando paralelismo donde sea posible e instrumentación (logging) en el 100% de las herramientas.

## 🎯 Objetivo
Reducir la latencia percibida por el usuario y proporcionar métricas precisas para la depuración de cuellos de botella (Red vs Cómputo vs SQL).

---

## 🏗️ 1. Refactorización (Paralelización)

Identificamos herramientas que hacen múltiples llamadas secuenciales a BigQuery.

### ⚡ `get_yearly_attrition` (en `hr_metrics.py`)
*   **Estado Actual:** Ejecuta `query_kpi` (Resumen Anual) y LUEGO `_fetch_yearly_series` (Gráfico Mensual).
*   **Problema:** Espera lineal (`T_KPI + T_CHART`).
*   **Solución:** Mover ambas llamadas a un `ThreadPoolExecutor`.
*   **Ganancia Estimada:** ~3-4 segundos.

### ✅ `get_monthly_trend` (en `hr_metrics.py`)
*   **Estado:** **Optimizado**. Ya usa paralelismo para comparar años.

---

## 📡 2. Instrumentación Global (Sensores [PERF])

Para todas las demás herramientas (Single-Query), inyectaremos logs estandarizados `[PERF]` para monitorear:
1.  **SQL Build Time:** Cuánto tarda Python en armar el string.
2.  **BigQuery Exec Time:** Latencia de red + Motor de BQ.
3.  **Pandas Processing:** Costo de serialización/transformación.

### Lista de Herramientas a Instrumentar:
| Archivo | Herramienta | Tipo | Acción |
| :--- | :--- | :--- | :--- |
| `turnover.py` | `get_turnover_deep_dive` | SQL + Pandas | Inyectar Logs |
| `leavers.py` | `get_leavers_list` | SQL | Inyectar Logs |
| `leavers.py` | `get_leavers_distribution` | SQL | Inyectar Logs |
| `hr_metrics.py` | `get_headcount_stats` | SQL | Inyectar Logs |
| `hr_metrics.py` | `get_talent_alerts` | SQL | Inyectar Logs |

---

## 🤖 3. Agentes & Router
*   **Router Logic:** El router ya mide "Planning Time" y "Tool Time".
*   **Acción:** Revisar si podemos añadir logs de "Overhead" (tiempo perdido entre recibir respuesta del LLM y ejecutar tool).

---

## 📅 Roadmap de Ejecución
1.  **Fase 1:** Refactorizar `get_yearly_attrition` (Thread Pool).
2.  **Fase 2:** Inyectar Sensores en `turnover.py` y `leavers.py`.
3.  **Fase 3:** Inyectar Sensores en resto de `hr_metrics.py`.
4.  **Fase 4:** Prueba Integradora (Smoke Test).
