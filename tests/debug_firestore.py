
import sys
import os
import asyncio
from dotenv import load_dotenv

# Add project root
sys.path.append(os.getcwd())
load_dotenv()

from app.services.firestore import get_firestore_service
from app.core.config import get_settings

async def test_firestore():
    settings = get_settings()
    print(f"🚀 Testing Firestore Connection...")
    print(f"   Project: {settings.PROJECT_ID}")
    print(f"   Collection: {settings.FIRESTORE_COLLECTION}")
    
    try:
        service = get_firestore_service()
        print(f"✅ Service Initialized")
        
        # Test Write
        test_id = "debug-session-123"
        data = {"status": "debug_ok", "timestamp": "now"}
        print(f"⏳ Attempting Write to {test_id}...")
        await service.save_session(test_id, data)
        print(f"✅ Write Success")
        
        # Test Read
        print(f"⏳ Attempting Read from {test_id}...")
        result = await service.get_session(test_id)
        print(f"✅ Read Success: {result}")
        
    except Exception as e:
        print(f"\n❌ FIRESTORE ERROR:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_firestore())
