"""
Test script para verificar que get_monthly_trend devuelve data_series correctamente
"""
import sys
sys.path.insert(0, 'C:/Users/Lenovo/OneDrive/Documents/adk-people-analytics-backend')

from app.ai.tools.bq_queries.hr_metrics import get_monthly_trend
import json

print("=" * 80)
print("TEST: get_monthly_trend(year=2025)")
print("=" * 80)

try:
    result = get_monthly_trend(year=2025, segment=None)
    
    print("\n✅ Función ejecutada sin errores\n")
    print("RESULTADO JSON:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Verificar estructura
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE ESTRUCTURA:")
    print("=" * 80)
    
    if result.get("response_type") == "visual_package":
        print("✅ response_type: visual_package")
    else:
        print(f"❌ response_type: {result.get('response_type')}")
    
    content = result.get("content", [])
    print(f"\n📦 Número de bloques en content: {len(content)}")
    
    for i, block in enumerate(content):
        block_type = block.get("type")
        print(f"\n  Bloque {i}: type = '{block_type}'")
        
        if block_type == "data_series":
            print("  ✅ ¡ENCONTRADO BLOQUE DATA_SERIES!")
            payload = block.get("payload", {})
            metadata = block.get("metadata", {})
            
            print(f"    - months: {len(payload.get('months', []))} elementos")
            print(f"    - rotacion_general: {len(payload.get('rotacion_general', []))} elementos")
            print(f"    - rotacion_voluntaria: {len(payload.get('rotacion_voluntaria', []))} elementos")
            print(f"    - metadata: {metadata}")
            
            if len(payload.get('months', [])) == 12:
                print("  ✅ Tiene 12 meses completos")
            else:
                print(f"  ⚠️ Solo tiene {len(payload.get('months', []))} meses")
    
    # Verificar si hay data_series
    has_data_series = any(block.get("type") == "data_series" for block in content)
    
    print("\n" + "=" * 80)
    if has_data_series:
        print("✅ RESULTADO: Backend está enviando data_series correctamente")
    else:
        print("❌ PROBLEMA: NO se encontró bloque data_series en la respuesta")
        print("   Los bloques encontrados fueron:")
        for block in content:
            print(f"   - {block.get('type')}")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ ERROR al ejecutar la función:")
    print(f"   {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
