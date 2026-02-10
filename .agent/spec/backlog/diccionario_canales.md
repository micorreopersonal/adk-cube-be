### CONFIGURACIÓN DE DICCIONARIO SEMÁNTICO: DIMENSIÓN CANALES (UO3)
**Objetivo:** Mapear terminología de negocio ("Canales", "FFVV Vida") a la columna técnica `uo3` de BigQuery para habilitar comparativas multidimensionales.

---

#### 1. REGLAS DE MAPEO SEMÁNTICO (ENTITY RESOLUTION)
Cuando el usuario mencione "Canal" o "Canales", el agente debe apuntar a la columna: `uo3`.

| Término de Negocio (Usuario) | Valor Técnico en BigQuery (`uo3`) | Segmento Asociado |
| :--- | :--- | :--- |
| **FFVV Vida** | `FFVV Multiproducto` | FFVV |
| **Fuerza de Ventas Vida** | `FFVV Multiproducto` | FFVV |
| **FFVV Multiproducto** | `FFVV Multiproducto` | FFVV |
| **FFVV Convenios** | `FFVV Convenios` | FFVV |
| **FFVV Rentas** | `FFVV Rentas` | FFVV |
| **BBVA** | `BBVA` | Bancaseguros |
| **Canales Directos** | `CANALES DIRECTOS` | Comercial |
| **Canales Indirectos** | `CANALES INDIRECTOS` | Comercial |
| **Corredores Estratégicos** | `CORREDORES ESTRATEGICOS` | Comercial |
| **Soluciones al Cliente** | `SOLUCIONES AL CLIENTE` | Operaciones |
| **Tribu P&C** | `TRIBU P&C` | Producto |
| **Tribu Vida** | `TRIBU VIDA` | Producto |


#### 2. LÓGICA DE PROCESAMIENTO PARA CONSULTAS COMPARATIVAS
**Escenario de ejemplo:** "¿Puedes comparar la rotación mensual de la FFVV Vida con la FFVV Convenios y Rentas?"

**Instrucciones para el Agente:**
1. **Identificación de Filtros:**
   - Detectar "FFVV Vida" -> Traducir a `uo3 = 'FFVV Multiproducto'`.
   - Detectar "FFVV Convenios" -> Traducir a `uo3 = 'FFVV Convenios'`.
   - Detectar "FFVV Rentas" -> Traducir a `uo3 = 'FFVV Rentas'`.
2. **Cálculo de Métrica (Rotación Mensual):**
   - El agente debe aplicar la fórmula: `(Cesados del Mes en UO3 / Headcount Inicial del Mes en UO3)`.
3. **Visualización Sugerida:** Generar un gráfico de líneas con los meses del año 2025 para las 3 dimensiones de `uo3` seleccionadas.

#### 3. RESTRICCIONES DE SEGURIDAD Y CALIDAD
- **Criterio de Cese:** Para todas las comparativas de "Rotación Voluntaria" en estos canales, filtrar estrictamente por `motivo_cese = 'RENUNCIA'`.
- **Exclusión:** Al hablar de "Canales de Venta", el agente debe asegurar que se están considerando los datos de `Segmento = 'EMPLEADO FFVV'` para evitar mezclar datos administrativos, a menos que el usuario pida explícitamente "toda la UO3".