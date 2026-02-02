
import sys
import os
import asyncio
from dotenv import load_dotenv

# Force load env vars
load_dotenv()

# Add project root
sys.path.append(os.getcwd())

from app.api.routes import chat
from app.schemas.chat import ChatRequest, TokenData
from app.core.config import get_settings

# Mock classes
class MockRequest:
    def __init__(self, message):
        self.message = message
        self.session_id = "test-session-debug"
        self.context_profile = "EJECUTIVO"

class MockUser:
    def __init__(self):
        self.username = "admin"
        self.profile = "ADMIN"

async def run_debug():
    print("🚀 Starting Full Flow Debug...")
    
    settings = get_settings()
    print(f"DEBUG: Project={settings.PROJECT_ID}, Env={settings.ENV}")
    
    test_msg = "¿Cómo cerró la rotación de fuerza de ventas en 2025?"
    print(f"DEBUG: Processing message: '{test_msg}'")
    
    request = MockRequest(test_msg)
    user = MockUser()
    
    try:
        # Simulate the API call directly
        response = await chat(request, current_user=user)
        print("\n✅ API Response Success:")
        print(response)
        
    except Exception as e:
        print("\n❌ CRITICAL CRASH IN API LAYER:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_debug())
