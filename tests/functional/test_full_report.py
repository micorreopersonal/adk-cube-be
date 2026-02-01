import sys
import os
import requests
import json
import time

# Add parent directory to path to allow imports if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

BASE_URL = "http://localhost:8080"

def test_full_report_generation():
    """
    Script de prueba para validar la generación del BOLETÍN MENSUAL completo.
    Simula un perfil ANALISTA pidiendo todo el análisis en un solo prompt.
    """
    print("=== PRUEBA DE GENERACIÓN DE REPORTE (BOLETÍN MENSUAL) ===\n")
    
    # 1. Autenticación (Admin -> tiene permisos de Analista)
    print("1. Autenticando...")
    try:
        token_response = requests.post(
            f"{BASE_URL}/token",
            data={"username": "admin", "password": "p014654"},
            timeout=10
        )
        if token_response.status_code != 200:
            print(f"❌ Error Auth: {token_response.status_code}")
            return
        token = token_response.json()["access_token"]
        print("✅ Token obtenido (Admin/Analista)\n")
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar al servidor. Verifica el puerto 8000.")
        return
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Payload del Reporte Completo
    payload = {
        "message": "Genera el reporte mensual de rotación de enero 2025. Incluye métricas generales, comparativa por segmentos (FFVV vs ADMI) y detalle de fugas de talento clave (Hipers/Hipos).",
        "session_id": "report-session-2025-01",
        "context_profile": "ANALISTA" # Perfil con acceso total
    }

    print(f"2. Solicitando Reporte Completo para Enero 2025...")
    print(f"📝 Prompt: {payload['message']}")
    print(f"👤 Perfil simulado: {payload['context_profile']}")
    print("⏳ Esperando respuesta del agente (esto puede tardar unos segundos)...")

    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            headers=headers,
            json=payload,
            timeout=60 # Damos más tiempo porque hará múltiples llamadas a herramientas
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ REPORTE GENERADO EXITOSAMENTE ({elapsed:.2f}s)")
            print(f"{'='*60}")
            print(result['response'])
            print(f"{'='*60}")
            print(f"\n📊 Metadata de Ejecución:")
            print(f"   - Agente: {result.get('metadata', {}).get('agent_name', 'N/A')}")
        else:
            print(f"\n❌ TAREA FALLIDA ({elapsed:.2f}s)")
            print(f"   Status: {response.status_code}")
            print(f"   Error: {response.text}")

    except requests.exceptions.Timeout:
        print(f"\n⏱️ Timeout: El agente tardó más de 60s en generar el reporte.")
    except Exception as e:
        print(f"\n❌ Excepción durante la solicitud: {str(e)}")

if __name__ == "__main__":
    test_full_report_generation()
