# Diagnóstico: Narrativas AI No Disponibles

## 🔍 Causa Raíz Identificada

**Error 429 - RESOURCE_EXHAUSTED (Cuota de API Excedida)**

Las narrativas del reporte ejecutivo no se generan porque las llamadas a Gemini (Vertex AI) están siendo rechazadas por exceder la cuota de requests por minuto (RPM) o tokens por minuto (TPM).

---

## 📊 Evidencia del Diagnóstico

### Test Ejecutado:
```bash
python tests/test_direct_insight.py
```

### Logs Capturados:
```
2026-02-09 13:41:30 - app.ai.tools.executive_insights - ERROR - Error generating insight
'status': 'RESOURCE_EXHAUSTED'
error-code-429
```

### Resultado:
- **4/4 narrativas** retornaron `"[AI Narrative Unavailable]"`
- Causa: El decorador `@retry` intenta 3 veces, pero todas fallan con 429

---

## 🧬 Análisis del Código Actual

### `executive_insights.py` - Líneas 80-98

```python
@retry(
    retry=retry_if_exception_type(google.api_core.exceptions.ResourceExhausted),
    stop=stop_after_attempt(3),           # Solo 3 intentos
    wait=wait_exponential(multiplier=1, min=2, max=10),  # Espera: 2s, 4s, 8s (muy corto)
    reraise=True
)
def _generate_with_retry(self, prompt: str, max_tokens: int) -> str:
    response = self.client.models.generate_content(...)
    return response.text.strip()
```

**Problema:**
- La espera máxima entre reintentos es **10 segundos**
- Con cuota agotada, el sistema puede necesitar **30-60 segundos** para resetear
- Después de 3 fallos, lanza excepción que es capturada en línea 119 y retorna `"[AI Narrative Unavailable - Quota Exceeded]"`

---

## 🎯 Soluciones Propuestas

### Solución 1: **Aumentar Retry Wait Time** (Corto Plazo) ⚡

Modificar el decorador de retry para esperar más tiempo:

```python
@retry(
    retry=retry_if_exception_type(google.api_core.exceptions.ResourceExhausted),
    stop=stop_after_attempt(5),           # 5 intentos en lugar de 3
    wait=wait_exponential(multiplier=2, min=5, max=60),  # Espera: 5s, 10s, 20s, 40s, 60s
    reraise=True
)
```

**Beneficio:** Aumenta la probabilidad de éxito cuando hay picos temporales de tráfico

---

### Solución 2: **Rate Limiting entre Secciones** (Medio Plazo) 🎛️

Agregar delays intencionales entre la generación de narrativas:

```python
# En executive_report_orchestrator.py
import time

# Después de cada generación de insight:
insight_1 = ai_gen.generate_section_insight("critical_insight", ...)
time.sleep(2)  # Esperar 2 segundos antes de la siguiente llamada
```

**Beneficio:** Distribuye las llamadas a la API en el tiempo, evitando burst

---

### Solución 3: **Caching Agresivo** (Arquitectónico) 💾

El sistema ya tiene caching en Firestore, pero podemos mejorarlo:

#### 3.1 Aumentar TTL de Cache
```python
# Línea 60 en executive_insights.py - Actualmente comentado
# Activar TTL de 7 días para evitar regenerar durante la semana
if created_at and (datetime.now(created_at.tzinfo) - created_at).days > 7: 
    return None  # Regenerar solo después de 7 días
```

#### 3.2 Pre-generar Reportes
Crear un Cloud Scheduler que genere reportes del mes anterior cada 1ro del mes:

```python
# Script de pre-generación (ejecuta a las 2am del día 1)
# Genera reporte del mes anterior y lo cachea
report = generate_executive_report(previous_month)
# Las llamadas futuras reutilizarán el cache
```

**Beneficio:** Los reportes frecuentes (mensuales) ya estarán cacheados

---

### Solución 4: **Aumentar Cuota en Vertex AI** (Operacional) 📈

#### Pasos:
1. Ir a Google Cloud Console → Vertex AI → Quotas
2. Solicitar aumento de cuota para:
   - **Requests per minute (RPM):** De 60 → 300  
   - **Tokens per minute (TPM):** De 2M → 10M

**Beneficio:** Permite generar más narrativas simultáneamente

---

### Solución 5: **Fallback Graceful** (User Experience) 🎨

En lugar de mostrar `"[AI Narrative Unavailable]"`, generar un placeholder contextual:

```python
# En línea 121 de executive_insights.py
except google.api_core.exceptions.ResourceExhausted:
    logger.error("❌ Quota exceeded after retries.")
    # En lugar de retornar texto genérico, usar datos del contexto
    return self._generate_fallback_narrative(section_name, data_context)

def _generate_fallback_narrative(self, section: str, data: Dict) -> str:
    """Genera narrativa básica sin LLM cuando hay errores de cuota."""
    if section == "critical_insight":
        actual_rate = data.get('headline_actual', {}).get('tasa', 0)
        prev_rate = data.get('headline_prev', {}).get('tasa', 0)
        delta = actual_rate - prev_rate
        
        trend = "incremento" if delta > 0 else "reducción"
        return f"La tasa de rotación actual es {actual_rate:.1f}%, representando un {trend} de {abs(delta):.1f} puntos respecto al período anterior."
    
    # Similar logic for other sections...
    return "Narrativa AI temporalmente no disponible. Los datos visuales están disponibles arriba."
```

**Beneficio:** Mejor UX - el usuario ve al menos un resumen básico en lugar de un error

---

## 🚀 Plan de Implementación Recomendado

###  Fase 1: Quick Wins (Hoy) ✅
1. ✅ Aumentar retry attempts: 3 → 5
2. ✅ Aumentar max wait time: 10s → 60s
3. ✅ Agregar `time.sleep(2)` entre narrativas del orchestrator

### Fase 2: Mejoras Estructurales (Esta Semana) 🔧
4. Activar TTL de cache (7 días)
5. Implementar fallback narratives contextuales
6. Solicitar aumento de cuota en Vertex AI

### Fase 3: Arquitectónico (Próximo Sprint) 🏗️
7. Implementar Cloud Scheduler para pre-generación
8. Dashboard de monitoreo de cuota/uso de API

---

## 📝 Archivos a Modificar

### 1. `app/ai/tools/executive_insights.py`
- Líneas 80-84: Aumentar retry config
- Líneas 119-124: Mejorar mensajes de error
- Agregar: `_generate_fallback_narrative()`

### 2. `app/ai/tools/executive_report_orchestrator.py`
- Después de cada `ai_gen.generate_section_insight()`: Agregar `time.sleep(2)`

---

## ✅ Criterios de Aceptación

Después de implementar Fase 1:

- [ ] Reporte ejecutivo de año completo (2025) genera **mínimo 3/6 narrativas** exitosas
- [ ] Errores 429 se retrantan automáticamente con espera exponencial  
- [ ] Logs muestran `"🔄 Retrying after 429..."` en lugar de fallar inmediatamente
- [ ] Cache hits reducen llamadas nuevas al LLM en **>70%**

---

## 🎯 Próximos Pasos Inmediatos

1. **Implementar Solución 1** (aumentar retry wait)
2. **Implementar Solución 2** (rate limiting)
3. **Re-ejecutar test**: `python tests/test_narrative_diagnosis.py --period 2025`
4. **Validar mejora**: Al menos 50% de narrativas deben generarse exitosamente
