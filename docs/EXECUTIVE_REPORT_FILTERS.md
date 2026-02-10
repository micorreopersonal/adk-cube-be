# Capacidades de Filtrado - Reporte Ejecutivo

## ✅ Dimensiones Temporales Soportadas

El reporte ejecutivo acepta **múltiples formatos de período** a través del parámetro `periodo_anomes`:

### 1. **Mes Específico** (YYYYMM)
```python
generate_executive_report("202501")  # Enero 2025
generate_executive_report("202412")  # Diciembre 2024
```
**Display:** "Enero 2025", "Diciembre 2024"

### 2. **Trimestre** (YYYYQN)
```python
generate_executive_report("2025Q1")  # Q1 2025 (Ene-Mar)
generate_executive_report("2024Q4")  # Q4 2024 (Oct-Dic)
```
**Display:** "Q1 2025", "Q4 2024"

### 3. **Año Completo** (YYYY)
```python
generate_executive_report("2025")   # Todo el año 2025
generate_executive_report("2024")   # Todo el año 2024
```
**Display:** "Año 2025", "Año 2024"

### 4. **Rango Personalizado** (YYYYMM-YYYYMM)
```python
generate_executive_report("202501-202503")  # Enero a Marzo 2025
generate_executive_report("202401-202412")  # Todo 2024
```
**Display:** "Ene 2025 - Mar 2025", "Ene 2024 - Dic 2024"

---

## ✅ Filtros Organizacionales Soportados

### 1. **Toda la Compañía** (Sin filtro)
```python
generate_executive_report("202501")  # uo2_filter = None (default)
```
Analiza **todos** los datos sin restricción de división/UO2.

### 2. **División Específica** (uo2_filter)
```python
generate_executive_report("202501", uo2_filter="ESTRATEGIA")
generate_executive_report("202501", uo2_filter="OPERACIONES")
```

El filtro `uo2_filter` se aplica a **todas las queries** del reporte:
- Headlines (KPIs actuales y anteriores)
- Segmentación (ADMIN vs FFVV)
- Rotación Voluntaria
- Fuga de Talento
- Tendencias temporales

---

## 🔍 Implementación Técnica

### Función Principal
```python
def generate_executive_report(
    periodo_anomes: str,           # YYYY, YYYYQN, YYYYMM, YYYYMM-YYYYMM
    uo2_filter: Optional[str] = None,  # División específica o None para toda
    sections: Optional[List[str]] = None  # Secciones específicas (opcional)
) -> dict:
```

### Aplicación de Filtros
El filtro `uo2_filter` se inyecta automáticamente en `build_query_sequence()`:

```python
# Líneas 159-160
base_filters = get_period_filters(parsed)
if uo2_filter:
    base_filters.append({"dimension": "uo2", "value": uo2_filter})
```

Y se propaga a:
- **base_filters:** Período actual
- **prev_filters:** Período anterior
- **trend_filters:** Contexto anual/rango

---

## 📊 Ejemplos de Uso

### Ejemplo 1: Reporte Mensual - Toda la Compañía
```python
report = generate_executive_report("202501")
```
- **Período:** Enero 2025
- **Alcance:** Toda la organización
- **Comparación:** vs Diciembre 2024

### Ejemplo 2: Reporte Trimestral - División Específica
```python
report = generate_executive_report("2025Q1", uo2_filter="VENTAS")
```
- **Período:** Q1 2025 (Ene-Mar)
- **Alcance:** Solo división VENTAS
- **Comparación:** vs Q4 2024 (solo VENTAS)

### Ejemplo 3: Reporte Anual - Toda la Compañía
```python
report = generate_executive_report("2024")
```
- **Período:** Todo el año 2024
- **Alcance:** Toda la organización
- **Comparación:** vs 2023

### Ejemplo 4: Rango Personalizado - División Específica
```python
report = generate_executive_report("202501-202506", uo2_filter="IT")
```
- **Período:** Ene-Jun 2025 (6 meses)
- **Alcance:** Solo división IT
- **Tendencia:** Evolución mensual dentro del rango

---

## ⚠️ Limitaciones Actuales

### No Soportado (Próximas Mejoras)
1. **Multi-UO2 (varias divisiones a la vez):**
   - Actualmente: `uo2_filter="VENTAS"` ✅
   - No soportado: `uo2_filter=["VENTAS", "IT"]` ❌
   
2. **Filtros adicionales simultáneos:**
   - No se puede combinar `uo2_filter` + `segmento_filter` en el mismo parámetro
   - Solución temporal: El Registry ya filtra por default `segmento != 'PRACTICANTE'`

3. **Comparación de múltiples períodos:**
   - Actualmente: Solo se compara con el período inmediatamente anterior
   - No soportado: Comparar 2025 vs 2023 (salto de períodos)

---

## 🎯 Próximos Pasos Sugeridos

Para expandir las capacidades de filtrado:

1. **Soporte Multi-División:**
   ```python
   uo2_filter=["VENTAS", "IT", "OPERACIONES"]
   ```

2. **Filtros Adicionales:**
   ```python
   generate_executive_report(
       "202501",
       filters={
           "uo2": "VENTAS",
           "tipo_vinculacion": "Plazo Fijo",
           "genero": "Femenino"
       }
   )
   ```

3. **Comparación Flexible:**
   ```python
   generate_executive_report(
       "202501",
       compare_to="202312"  # Comparar Ene 2025 vs Dic 2023
   )
   ```
