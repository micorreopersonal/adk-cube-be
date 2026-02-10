"""
Simple SSE Test for Executive Report Streaming
-----------------------------------------------
Tests the progressive streaming without complex dependencies.
Uses requests library which is simpler than aiohttp for testing.
"""

import requests
import json
import time

def get_auth_token():
    """Get authentication token."""
    print("🔐 Obteniendo token de autenticación...")
    
    response = requests.post(
        "http://localhost:8080/token",
        data={"username": "ejecutivo", "password": "123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code != 200:
        print(f"❌ Error al autenticar: {response.status_code}")
        print(response.text)
        return None
    
    token_data = response.json()
    token = token_data.get("access_token")
    print(f"✅ Token obtenido: {token[:30]}...\n")
    return token


def test_streaming_report():
    """Test SSE streaming endpoint."""
    print("\n" + "="*80)
    print("🔍 TEST: Executive Report Progressive Streaming (SSE)")
    print("="*80)
    print("Endpoint: POST /api/executive-report-stream")
    print("Period: 202501 (Enero 2025)")
    print("="*80 + "\n")
    
    # Get token
    token = get_auth_token()
    if not token:
        return
    
    # Stream endpoint
    url = "http://localhost:8080/api/executive-report-stream"
    params = {"period": "202501"}
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream"
    }
    
    print("📡 Conectando al stream...\n")
    
    try:
        # Use stream=True to get SSE events
        response = requests.post(url, params=params, headers=headers, stream=True, timeout=300)
        
        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text)
            return
        
        print("✅ Conectado! Recibiendo secciones progresivamente...\n")
        
        section_count = 0
        insights_count = 0
        start_time = time.time()
        last_progress = 0
        
        # Read SSE stream line by line
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            
            # SSE format: "data: {...}"
            if line.startswith('data:'):
                data_json = line[5:].strip()  # Remove 'data:' prefix
                
                try:
                    section_data = json.loads(data_json)
                    section_id = section_data.get('section_id')
                    progress = section_data.get('progress', 0)
                    blocks = section_data.get('blocks', [])
                    status = section_data.get('status', 'ok')
                    
                    # Handle error
                    if status == 'error':
                        print(f"\n❌ Error en stream: {section_data.get('error')}")
                        break
                    
                    # Handle completion
                    if section_id == 'complete':
                        elapsed = time.time() - start_time
                        print(f"\n✅ REPORTE COMPLETADO (100%) en {elapsed:.1f}s")
                        break
                    
                    # Count section
                    if section_id not in ['header', 'complete']:
                        section_count += 1
                    
                    # Count insights (AI-generated narratives)
                    for block in blocks:
                        if block.get('variant') in ['insight', 'standard']:
                            if block.get('payload') and '[AI Narrative Unavailable]' not in block.get('payload', ''):
                                insights_count += 1
                    
                    # Show progress update
                    if progress > last_progress:
                        elapsed = time.time() - start_time
                        print(f"📦 [{elapsed:5.1f}s] Sección: {section_id:20s} | Progress: {progress:3d}% | Bloques: {len(blocks):2d}")
                        
                        # Show first insight preview if available
                        for block in blocks:
                            if block.get('variant') in ['insight', 'standard']:
                                payload = block.get('payload', '')
                                if payload and len(payload) > 10:
                                    preview = payload[:80].replace('\n', ' ')
                                    print(f"   💡 Insight: {preview}...")
                                    break
                        
                        last_progress = progress
                    
                except json.JSONDecodeError as e:
                    print(f"⚠️  Error parsing JSON: {e}")
                    print(f"   Raw: {data_json[:100]}...")
                    continue
        
        # Summary
        total_time = time.time() - start_time
        print("\n" + "="*80)
        print("📊 RESUMEN DEL TEST")
        print("="*80)
        print(f"Tiempo total: {total_time:.1f}s")
        print(f"Secciones recibidas: {section_count}")
        print(f"Insights AI generados exitosamente: {insights_count}")
        
        # Validation
        if section_count >= 5:
            print(f"\n✅ ÉXITO: Recibidas {section_count} secciones progresivamente")
        else:
            print(f"\n❌ FALLO: Solo {section_count} secciones (esperado mínimo 5)")
        
        if insights_count >= 5:
            print(f"✅ ÉXITO: {insights_count} insights AI generados correctamente")
        elif insights_count > 0:
            print(f"⚠️  PARCIAL: Solo {insights_count} insights generados (esperado mínimo 5)")
        else:
            print(f"❌ FALLO: No se generaron insights AI")
        
        # Performance assessment
        if section_count > 0:
            avg_time_per_section = total_time / section_count
            print(f"\n⏱️  Tiempo promedio por sección: {avg_time_per_section:.1f}s")
            
            if avg_time_per_section < 15:
                print("✅ RENDIMIENTO: Excelente (< 15s por sección)")
            elif avg_time_per_section < 25:
                print("⚠️  RENDIMIENTO: Aceptable (15-25s por sección)")
            else:
                print("❌ RENDIMIENTO: Lento (> 25s por sección)")
        
    except requests.exceptions.Timeout:
        print("❌ Timeout: El servidor tardó más de 5 minutos")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Error de conexión: {e}")
        print("   Verifica que uvicorn esté corriendo en localhost:8080")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_streaming_report()
