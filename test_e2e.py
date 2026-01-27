"""
Test end-to-end del flujo completo
"""
import requests
import json

url = "http://localhost:8080/api/chat"
payload = {
    "message": "dame la tendencia mensual completa de 2025",
    "session_id": "test-session-final",
    "profile": "ADMIN"
}

print("=" * 80)
print("TEST END-TO-END: Enviando request al backend")
print("=" * 80)
print(f"\nURL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

try:
    response = requests.post(url, json=payload, timeout=30)
    
    print(f"Status Code: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        
        # Guardar respuesta completa
        with open('test_response_full.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print("✅ Respuesta recibida exitosamente\n")
        print("=" * 80)
        print("VERIFICACIÓN:")
        print("=" * 80)
        
        response_type = data.get("response_type")
        print(f"\nresponse_type: {response_type}")
        
        content = data.get("content", [])
        print(f"Número de bloques: {len(content)}\n")
        
        has_data_series = False
        for i, block in enumerate(content):
            block_type = block.get("type")
            print(f"  Bloque {i}: {block_type}")
            
            if block_type == "data_series":
                has_data_series = True
                payload_data = block.get("payload", {})
                print(f"    ✅ DATA_SERIES ENCONTRADO!")
                print(f"    - months: {len(payload_data.get('months', []))} elementos")
                print(f"    - rotacion_general: {payload_data.get('rotacion_general', [])[:3]}...")
        
        print("\n" + "=" * 80)
        if has_data_series:
            print("✅✅✅ ÉXITO TOTAL: El agente llamó a get_monthly_trend y envió data_series")
        else:
            print("❌ PROBLEMA: El agente NO llamó a get_monthly_trend")
            print("   Probablemente generó texto en lugar de usar la tool")
        print("=" * 80)
        
        print(f"\nRespuesta completa guardada en: test_response_full.json")
        
    else:
        print(f"❌ Error HTTP: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
