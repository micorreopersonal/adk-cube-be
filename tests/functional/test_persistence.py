import sys
import os
import requests
import time

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

BASE_URL = "http://localhost:8000"

def test_persistence_flow():
    """
    Prueba Funcional de Persistencia de Sesión.
    Verifica que el agente recuerda información entre dos turnos separados.
    """
    print("=== PRUEBA DE PERSISTENCIA FIRESTORE (Chat Memory) ===\n")
    
    # 1. Autenticación
    try:
        token_resp = requests.post(f"{BASE_URL}/token", data={"username": "admin", "password": "p014654"})
        if token_resp.status_code != 200:
            print(f"❌ Error Auth: {token_resp.text}")
            return
        token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
    except Exception as e:
        print(f"❌ Error conectando: {e}")
        return

    session_id = f"test-persistence-{int(time.time())}"
    print(f"🆔 Session ID: {session_id}")

    # 2. Turno 1: Dar contexto ("Me llamo Juan")
    print("\n👉 Turno 1: 'Hola, me llamo Juan. Recuérdalo.'")
    payload_1 = {
        "message": "Hola, me llamo Juan. Por favor recuerda mi nombre para la siguiente pregunta.",
        "session_id": session_id,
        # Usamos perfil ADMIN para que no estorbe logic de negocio, 
        # aunque el HR Agent quizás no esté optimizado para chitchat, debería tener memoria básica del modelo.
        "context_profile": "ADMIN" 
    }
    resp_1 = requests.post(f"{BASE_URL}/chat", headers=headers, json=payload_1)
    print(f"🤖 Respuesta 1: {resp_1.json().get('response', 'Error')}")

    # 3. Simular desconexión / espera
    print("\n⏳ Simulando espera y reconexión...")
    time.sleep(2)

    # 4. Turno 2: Preguntar por contexto ("¿Cómo me llamo?")
    print("\n👉 Turno 2: '¿Cuál es mi nombre?'")
    payload_2 = {
        "message": "¿Cómo me llamo según lo que te acabo de decir?",
        "session_id": session_id,
        "context_profile": "ADMIN"
    }
    resp_2 = requests.post(f"{BASE_URL}/chat", headers=headers, json=payload_2)
    response_text = resp_2.json().get('response', '')
    print(f"🤖 Respuesta 2: {response_text}")

    # 5. Validación
    if "Juan" in response_text or "juan" in response_text:
        print("\n✅ ÉXITO: El agente recordó el nombre.")
    else:
        print("\n❌ FALLO: El agente no recordó el nombre (Posible fallo de persistencia).")

if __name__ == "__main__":
    test_persistence_flow()
