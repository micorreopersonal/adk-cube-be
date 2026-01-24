import sys
import os
import requests
import json

# Add parent directory to path to allow imports if needed, 
# though for functional tests running against localhost port, standard requests are enough.
# Just ensuring script is standalone.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

BASE_URL = "http://localhost:8000"

def test_tool_execution():
    """
    Script de prueba para validar la ejecución de las herramientas del agente
    con diferentes perfiles de usuario (RBAC).
    """
    print("=== PRUEBA DE HERRAMIENTAS DEL AGENTE (E2E) ===\n")
    
    # 1. Obtener token de autenticación
    print("1. Autenticando...")
    try:
        token_response = requests.post(
            f"{BASE_URL}/token",
            data={"username": "admin", "password": "p014654"},
            timeout=5
        )
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar al servidor. Verifica que Uvicorn esté corriendo en el puerto 8000.")
        return
    
    if token_response.status_code != 200:
        print(f"❌ Error en autenticación: {token_response.status_code}")
        return
    
    token = token_response.json()["access_token"]
    print("✅ Token obtenido correctamente\n")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Casos de prueba
    test_cases = [
        {
            "name": "Caso A: Rotación General (Enero 2025 - Test Fallback)",
            "payload": {
                "message": "¿Cuál fue la tasa de rotación general en enero de 2025?",
                "session_id": "test-session-001",
                "context_profile": "EJECUTIVO"
            },
            "expected_tools": ["get_monthly_attrition"]
        },
        {
            "name": "Caso B: Comparativa Segmentos (Perfil ANALISTA)",
            "payload": {
                "message": "Analiza la rotación voluntaria de ADMI vs FFVV para enero 2025.",
                "session_id": "test-session-002",
                "context_profile": "ANALISTA"
            },
            "expected_tools": ["get_monthly_attrition"]
        },
        {
            "name": "Caso C: Alerta de Talento (Perfil ADMIN)",
            "payload": {
                "message": "¿Qué talento clave (Hipers o Hipos) perdimos en enero 2025?",
                "session_id": "test-session-003",
                "context_profile": "ADMIN"
            },
            "expected_tools": ["get_talent_alerts"]
        }
    ]
    
    # 3. Ejecutar casos de prueba
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"{i}. {test_case['name']}")
        print(f"{'='*60}")
        print(f"📝 Mensaje: {test_case['payload']['message']}")
        print(f"👤 Perfil: {test_case['payload']['context_profile']}")
        print(f"🔧 Herramientas esperadas: {', '.join(test_case['expected_tools'])}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                headers=headers,
                json=test_case["payload"],
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ Status: {response.status_code}")
                # print(f"🤖 Respuesta completa: {result['response']}") 
                print(f"🤖 Respuesta del agente (extracto):")
                print(f"   {result['response'][:200]}...")
                print(f"\n📊 Metadata:")
                print(f"   - Agente: {result.get('metadata', {}).get('agent_name', 'N/A')}")
            else:
                print(f"\n❌ Error {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"\n⏱️ Timeout: La consulta tardó más de 30 segundos")
        except Exception as e:
            print(f"\n❌ Excepción: {str(e)}")
    
    print(f"\n{'='*60}")
    print("✅ Pruebas completadas")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    test_tool_execution()
