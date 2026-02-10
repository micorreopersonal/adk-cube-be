import requests
import json

def trigger_stream():
    # 1. Get Token (Mocking logic or direct call)
    # Since it's local dev, let's assume we can get a token or use a known one if we know it.
    # Actually, I'll just call the /token endpoint in the script.
    
    BASE_URL = "http://localhost:8888"
    
    print("🔐 Obteniendo token...")
    auth_res = requests.post(
        f"{BASE_URL}/token",
        data={"username": "admin", "password": "p014654"}
    )
    if auth_res.status_code != 200:
        print(f"❌ Error auth: {auth_res.text}")
        return
        
    token = auth_res.json()["access_token"]
    print("✅ Token obtenido.")
    
    # 2. Call Stream
    print("📡 Llamando al stream...")
    url = f"{BASE_URL}/executive-report-stream?period=2025&sections=headline"
    
    # We use stream=True for SSE
    with requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        stream=True
    ) as r:
        if r.status_code != 200:
            print(f"❌ Error stream: {r.status_code} - {r.text}")
            return
            
        for line in r.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(f"📦 Recibido: {decoded_line[:100]}...")
                # Solo procesamos un par de eventos para confirmar
                if "headline" in decoded_line:
                    break

if __name__ == "__main__":
    trigger_stream()
