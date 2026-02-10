"""
Test: Partial Report Generation (Solo Bloque 1 - Headline)
----------------------------------------------------------
Valida:
1. Bug fix: KPIs muestran valores correctos (no 0%)
2. Generación parcial: Solo sección 'headline' se genera
3. Contexto AI: Insight usa datos correctos
"""

import requests
import json
import time

def test_headline_only():
    """
    Test endpoint SSE con parámetro sections='headline'
    """
    print("\n" + "="*80)
    print("🔍 TEST: Generación Parcial - Solo Bloque 1 (Headline)")
    print("="*80)
    print("Endpoint: POST /executive-report-stream")
    print("Period: 2025")
    print("Sections: headline (solo bloque 1)")
    print("="*80 + "\n")
    
    # Autenticación
    print("🔐 Obteniendo token...")
    auth_response = requests.post(
        "http://localhost:8080/token",
        data={"username": "ejecutivo", "password": "123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if auth_response.status_code != 200:
        print(f"❌ Error de autenticación: {auth_response.status_code}")
        print(auth_response.text)
        return
    
    token = auth_response.json().get("access_token")
    print(f"✅ Token obtenido\n")
    
    # Stream endpoint con parámetro sections
    url = "http://localhost:8080/executive-report-stream"
    params = {
        "period": "2025",
        "sections": "headline"  # Solo bloque 1
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream"
    }
    
    print("📡 Conectando al stream (solo headline)...\n")
    
    try:
        response = requests.post(url, params=params, headers=headers, stream=True, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text)
            return
        
        print("✅ Conectado! Recibiendo datos...\n")
        
        sections_received = []
        kpi_values = {}
        insight_text = ""
        start_time = time.time()
        
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith('data:'):
                continue
            
            data_json = line[5:].strip()
            
            try:
                section_data = json.loads(data_json)
                section_id = section_data.get('section_id')
                blocks = section_data.get('blocks', [])
                progress = section_data.get('progress', 0)
                status = section_data.get('status', 'ok')
                
                if status == 'error':
                    print(f"❌ Error: {section_data.get('error')}")
                    break
                
                if section_id == 'complete':
                    elapsed = time.time() - start_time
                    print(f"\n✅ Generación completada en {elapsed:.1f}s\n")
                    break
                
                sections_received.append(section_id)
                print(f"📦 Sección recibida: {section_id} (progress: {progress}%)")
                print(f"   Bloques en sección: {len(blocks)}")
                
                # Extraer KPIs y insight
                for block in blocks:
                    block_type = block.get('type')
                    variant = block.get('variant')
                    payload = block.get('payload')
                    
                    # Extraer valores de KPIs
                    if block_type == 'kpi_row' and isinstance(payload, dict):
                        items = payload.get('items', [])
                        for item in items:
                            label = item.get('label', '')
                            value = item.get('value', 0)
                            kpi_values[label] = value
                            print(f"   📊 KPI: {label} = {value}")
                    
                    # Extraer insight
                    if variant == 'insight' and isinstance(payload, str):
                        insight_text = payload
                        preview = payload[:100].replace('\n', ' ')
                        print(f"   💡 Insight preview: {preview}...")
                
                print("")
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Error parsing JSON: {e}")
                continue
        
        # Validación
        print("="*80)
        print("📊 VALIDACIÓN DE RESULTADOS")
        print("="*80)
        
        # 1. Verificar que solo se recibió 'headline'
        non_header_sections = [s for s in sections_received if s != 'header']
        print(f"\n1. Generación Parcial:")
        print(f"   Secciones solicitadas: ['headline']")
        print(f"   Secciones recibidas: {non_header_sections}")
        
        if non_header_sections == ['headline']:
            print(f"   ✅ CORRECTO: Solo se generó la sección solicitada")
        else:
            print(f"   ❌ ERROR: Se generaron secciones adicionales: {non_header_sections}")
        
        # 2. Verificar que KPIs NO son 0% (bug fix)
        print(f"\n2. Bug Fix - KPIs con Valores Correctos:")
        tasa_rotacion = kpi_values.get('Tasa de Rotación Global (%)', 0)
        total_ceses = kpi_values.get('Total Ceses', 0)
        headcount = kpi_values.get('Headcount Promedio', 0)
        
        print(f"   Tasa de Rotación: {tasa_rotacion}%")
        print(f"   Total Ceses: {total_ceses}")
        print(f"   Headcount: {headcount}")
        
        if tasa_rotacion > 0 and total_ceses > 0:
            print(f"   ✅ CORRECTO: KPIs tienen valores reales (no 0%)")
        else:
            print(f"   ❌ ERROR: KPIs siguen en 0%")
        
        # 3. Verificar que insight tiene contenido útil
        print(f"\n3. Insight AI:")
        if len(insight_text) > 50 and "0%" not in insight_text[:200]:
            print(f"   ✅ CORRECTO: Insight generado con contexto válido")
            print(f"   Longitud: {len(insight_text)} caracteres")
        elif "[AI Narrative Unavailable]" in insight_text:
            print(f"   ❌ ERROR: Insight no disponible (error API)")
        elif "0%" in insight_text[:200]:
            print(f"   ⚠️ ADVERTENCIA: Insight menciona 0% (posible bug persiste)")
        else:
            print(f"   ⚠️ ADVERTENCIA: Insight muy corto ({len(insight_text)} chars)")
        
        # Resumen final
        print("\n" + "="*80)
        all_ok = (
            non_header_sections == ['headline'] and
            tasa_rotacion > 0 and
            total_ceses > 0 and
            len(insight_text) > 50
        )
        
        if all_ok:
            print("✅ TODAS LAS VALIDACIONES PASARON")
        else:
            print("⚠️ ALGUNAS VALIDACIONES FALLARON - Revisar arriba")
        print("="*80 + "\n")
        
    except requests.exceptions.Timeout:
        print("❌ Timeout: Más de 60 segundos")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Error de conexión: {e}")
        print("   Verifica que uvicorn esté corriendo")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_headline_only()
