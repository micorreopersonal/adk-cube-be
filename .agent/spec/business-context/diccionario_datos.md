### ESPECIFICACIÓN TÉCNICA: DICCIONARIO DE DATOS NL2SQL (ANTIGRAVITY) - V2.0

[cite_start]**Nombre de la Tabla:** `rimac-analytics.talento.tb_rotacion_maestra` [cite: 1]

---

#### 1. CATÁLOGO DE DIMENSIONES (MAPEO JERÁRQUICO DINÁMICO)
| Nombre Técnico | Nivel Teórico | Descripción de Negocio y Reglas |
| :--- | :--- | :--- |
| `uo1` | Nivel 1 | [cite_start]Gerencia General (Ancla superior). [cite: 1] |
| `uo2` | Nivel 2 | [cite_start]**Divisiones:** Finanzas, Talento, Tecnología, etc. (Nivel de reporte principal). [cite: 1, 383] |
| `uo3` | Nivel 3 | [cite_start]**Áreas:** El significado varía según la División (UO2). [cite: 1] |
| `uo4` | Nivel 4 | [cite_start]**Subgerencias:** Dependencia directa de Áreas. [cite: 1] |
| `uo5` | Nivel 5 | [cite_start]**Estructura Media:** CoEs, Jefaturas y otros según la División. [cite: 1, 276] |
| `uo6` | Nivel 6 | [cite_start]**Estructura Operativa:** Jefaturas de equipo (Nivel más granular). [cite: 1] |

> **Regla de Negocio para el Agente:** La profundidad de la jerarquía es variable. [cite_start]Si el usuario pide "Drill-down por área", el agente debe iterar de `uo2` hacia abajo, entendiendo que el nombre de la unidad es el valor contenido en la columna, independientemente de que la etiqueta del nivel sea distinta entre Divisiones. [cite: 1]

---

#### 2. DICCIONARIO DE MÉTRICAS Y LÓGICA TEMPORAL (TIME-INTELLIGENCE)
| Métrica | Definición SQL / Lógica | Fuente de Verdad |
| :--- | :--- | :--- |
| **HC Final (Mes actual)** | `COUNT(DISTINCT codigo_persona) WHERE estado = 'Activo' AND periodo = [Fecha Seleccionada]` | |
| **HC Inicial (Mes anterior)** | `COUNT(DISTINCT codigo_persona) WHERE estado = 'Activo' AND periodo = DATE_SUB([Fecha Seleccionada], INTERVAL 1 MONTH)` | |
| **Ceses Totales** | `COUNT(DISTINCT codigo_persona) WHERE estado = 'Cesado'` | |
| **Ceses Voluntarios** | `COUNT(DISTINCT codigo_persona) WHERE estado = 'Cesado' AND motivo_cese = 'RENUNCIA'` | |
| **Rotación Mensual %** | [cite_start]`(Ceses Totales del Mes) / (HC Inicial del Mes)` | [cite: 1258] |
| **Rotación Anualizada** | `(Suma de Ceses en el año) / (Promedio de HC Mensuales del año)` | |

---

#### 3. FILTROS PREESTABLECIDOS (ENTENDIMIENTO DE LENGUAJE NATURAL)
* [cite_start]**"Talento Top / High Potentials":** Filtrar por `mapeo_talento_ultimo_anio` IN (7, 8, 9). [cite: 1, 718]
* **"Fuerza de Ventas (FFVV)":** Filtrar por `segmento = 'EMPLEADO FFVV'`.
* [cite_start]**"Personal Administrativo (ADMI)":** Filtrar por `segmento != 'EMPLEADO FFVV'` y excluir `practicantes`. [cite: 1258]
* [cite_start]**"Tenencia / Antigüedad":** Usar `ts_anios` para promedios de permanencia. [cite: 1, 13]

---

#### 4. NOTAS DE IMPLEMENTACIÓN (PROMPTING)
1. **Contexto de "Renuncia":** Cualquier cese con el motivo "RENUNCIA" se clasifica como Voluntario.
2. [cite_start]**Denominadores:** Siempre verificar que el denominador (HC Inicial) corresponda al periodo anterior del numerador (Ceses). [cite: 1258]
3. **Ausencia de Metas:** El agente debe responder sobre datos reales y, ante comparativas, sugerir la creación de metas (Backlog de Negocio).