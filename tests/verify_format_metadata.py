"""
Test de verificación del sistema de metadata de formato
"""
from app.core.analytics.registry import METRICS_REGISTRY
from app.schemas.payloads import Dataset, MetricFormat

# Verificar estructura del registry
print("📋 Verificando METRICS_REGISTRY")
print("="*60)

for metric_key, metric_def in list(METRICS_REGISTRY.items())[:3]:
    print(f"\n✓ {metric_key}:")
    print(f"  Label: {metric_def.get('label', 'N/A')}")
    print(f"  Format: {metric_def.get('format', 'N/A')}")

# Verificar creación de Dataset con formato
print("\n\n📊 Verificando creación de Dataset con MetricFormat")
print("="*60)

metric_def = METRICS_REGISTRY["ceses_voluntarios"]
format_dict = metric_def["format"]

metric_format = MetricFormat(**format_dict)
print(f"\n✓ MetricFormat creado:")
print(f"  unit_type: {metric_format.unit_type}")
print(f"  symbol: {metric_format.symbol}")
print(f"  decimals: {metric_format.decimals}")

dataset = Dataset(
    label="Ceses Voluntarios",
    data=[462, 47, 29, 26, 25],
    format=metric_format
)

print(f"\n✓ Dataset JSON:")
import json
print(json.dumps(dataset.model_dump(), indent=2, ensure_ascii=False))

print("\n\n✅ Verificación completada con éxito!")
