import requests
import sys

BASE_URL = "http://localhost:8080"

def reset_session(session_id):
    # 1. Login
    try:
        resp = requests.post(f"{BASE_URL}/token", data={"username": "admin", "password": "p014654"})
        if resp.status_code != 200:
            print(f"❌ Auth failed: {resp.text}")
            return
        token = resp.json()["access_token"]
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # 2. Reset
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/session/reset", json={"session_id": session_id}, headers=headers)
    
    if resp.status_code == 200:
        print(f"✅ Session '{session_id}' cleared successfully.")
    else:
        print(f"⚠️ Failed to clear '{session_id}': {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    ids_to_reset = ["default", "report-session-2025-01", "report-session-2025-01-ANALISTA", "session-admin"]
    print("🧹 Cleaning Backend Sessions...")
    for sid in ids_to_reset:
        reset_session(sid)
