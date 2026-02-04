import asyncio
from app.services.firestore import get_firestore_service
from app.core.config.config import get_settings

async def reset_memory():
    try:
        settings = get_settings()
        service = get_firestore_service()
        
        # El ID de sesión que vimos en los logs
        session_id = "session-admin"
        
        print(f"🧹 Buscando sesion '{session_id}' en coleccion '{settings.FIRESTORE_COLLECTION}'...")
        
        # Acceder directamente al cliente para borrar
        doc_ref = service.client.collection(settings.FIRESTORE_COLLECTION).document(session_id)
        doc = await doc_ref.get()
        
        if doc.exists:
            await doc_ref.delete()
            print(f"✅ ¡Memoria Borrada Exitosamente! La sesion '{session_id}' ha sido eliminada.")
        else:
            print(f"⚠️ La sesion '{session_id}' no existe (o ya fue borrada).")
            
    except Exception as e:
        print(f"❌ Error al borrar memoria: {str(e)}")

if __name__ == "__main__":
    asyncio.run(reset_memory())
