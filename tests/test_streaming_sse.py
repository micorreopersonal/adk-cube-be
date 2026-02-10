"""
Test Script: Executive Report Streaming
----------------------------------------
Tests the progressive streaming of executive report with SSE.
"""

import asyncio
import aiohttp
import json

async def test_streaming_report():
    """
    Test SSE streaming endpoint for executive report.
    """
    print("\n" + "="*80)
    print("🔍 TEST: Executive Report Progressive Streaming (SSE)")
    print("="*80)
    print("Endpoint: POST /api/executive-report-stream")
    print("Period: 202501 (Enero 2025)")
    print("="*80 + "\n")
    
    url = "http://localhost:8080/api/executive-report-stream?period=202501"
    
    # Nota: Este endpoint requiere autenticación
    # Para testing, necesitas un token válido
    # Puedes obtenerlo con POST /token (username: admin, password: admin123)
    
    headers = {
        "Authorization": "Bearer YOUR_TOKEN_HERE",  # Reemplazar con token real
        "Accept": "text/event-stream"
    }
    
    print("📡 Conectando al stream...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                if response.status != 200:
                    print(f"❌ Error: HTTP {response.status}")
                    print(await response.text())
                    return
                
                print("✅ Conectado! Recibiendo secciones...\n")
                
                section_count = 0
                insights_count = 0
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if line_str.startswith('data:'):
                        data_json = line_str[5:].strip()  # Remove 'data:' prefix
                        
                        try:
                            section_data = json.loads(data_json)
                            section_id = section_data.get('section_id')
                            progress = section_data.get('progress', 0)
                            blocks = section_data.get('blocks', [])
                            status = section_data.get('status', 'ok')
                            
                            if status == 'error':
                                print(f"❌ Error en stream: {section_data.get('error')}")
                                break
                            
                            if section_id == 'complete':
                                print(f"\n✅ REPORTE COMPLETADO (100%)")
                                break
                            
                            section_count += 1
                            
                            # Count insights (AI-generated narratives)
                            for block in blocks:
                                if block.get('variant') in ['insight', 'standard']:
                                    insights_count += 1
                            
                            print(f"📦 Sección #{section_count}: {section_id} ({progress}% completado)")
                            print(f"   Bloques recibidos: {len(blocks)}")
                            
                            # Show first block preview
                            if blocks:
                                first_block = blocks[0]
                                block_type = first_block.get('type')
                                payload_preview = str(first_block.get('payload', ''))[:60]
                                print(f"   Preview: [{block_type}] {payload_preview}...")
                            
                            print("")
                            
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Error parsing JSON: {e}")
                            continue
                
                print("\n" + "="*80)
                print("📊 RESUMEN DEL TEST")
                print("="*80)
                print(f"Secciones recibidas: {section_count}")
                print(f"Insights AI generados: {insights_count}")
                
                if insights_count >= 5:
                    print(f"\n✅ ÉXITO: Al menos 5 insights AI generados correctamente")
                elif insights_count > 0:
                    print(f"\n⚠️  PARCIAL: Solo {insights_count} insights generados (esperado mínimo 5)")
                else:
                    print(f"\n❌ FALLO: No se generaron insights AI")
                
    except aiohttp.ClientError as e:
        print(f"❌ Error de conexión: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n⚠️  NOTA: Este test requiere que uvicorn esté corriendo en localhost:8080")
    print("   Comando: uvicorn app.main:app --port 8080 --reload\n")
    print("   También necesitas un token de autenticación válido.")
    print("   Obtener token: POST /token con username=admin, password=admin123\n")
    
    # Para ejecutar sin autenticación (solo para testing local):
    # Comentar temporalmente el Depends(get_current_user) en el endpoint
    
    asyncio.run(test_streaming_report())
