from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import logging

from app.core.config.config import get_settings
from app.schemas.chat import ChatRequest, ChatResponse, Token, TokenData, ResetSessionRequest
from app.core.auth.security import create_access_token, get_current_user
from app.core.auth.mock_users import get_user
# Note: This import will be updated in Phase 6, but putting correct one now
from app.ai.agents.router_logic import get_router 
from app.services.bigquery import get_bq_service
from app.services.storage import get_storage_service
from app.services.firestore import get_firestore_service

logger = logging.getLogger(__name__)

settings = get_settings()
# Instanciamos el router lógico (Orquestador de IA)
ai_router = get_router()

# Router de FastAPI
api_router = APIRouter()

@api_router.get("/")
async def root():
    return {
        "message": f"ADK Talent Analytics API is running on {settings.PROJECT_ID} (SOTA Architecture)",
        "project_id": settings.PROJECT_ID,
        "env": settings.ENV,
        "status": "healthy"
    }

@api_router.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.APP_ENV}

@api_router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # DEBUG LOGIN
    from app.main import log_debug
    logger.info(f"🔐 [LOGIN ATTEMPT] User: {form_data.username}")
    log_debug(f"🔐 [LOGIN ATTEMPT] User: {form_data.username}")

    # Limpiar inputs (Trim whitespace) para evitar errores de capa 8
    username_clean = form_data.username.strip()
    password_clean = form_data.password.strip()

    # Validación contra "Base de Datos" de Mock Users
    user_db = get_user(username_clean)
    
    if not user_db:
        log_debug(f"❌ [LOGIN FAIL] User not found: {username_clean}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user_db["password"] != password_clean:
        log_debug(f"❌ [LOGIN FAIL] Password mismatch for: {username_clean}. Expected: {user_db['password']}, Got: {password_clean}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    log_debug(f"✅ [LOGIN SUCCESS] User: {username_clean}")
    
    # Crear token incluyendo el perfil del usuario validado
    access_token = create_access_token(
        data={
            "sub": form_data.username,
            "profile": user_db["profile"]
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: TokenData = Depends(get_current_user)):
    """
    Endpoint principal para interactuar con el ecosistema de agentes.
    Requiere autenticación.
    """
    # Priorizar el perfil del token (seguro) sobre el del request (si existiera)
    user_profile = current_user.profile or request.context_profile or "EJECUTIVO"
    response_text = await ai_router.route(request.message, session_id=request.session_id, profile=user_profile)
    
    # Construir VisualDataPackage
    # from app.ai.utils.response_builder import ResponseBuilder (DEPRECATED)
    import json
    
    visual_package = None
    
    # 0. Caso Ideal: El Router ya devolvió un Diccionario (VisualDataPackage interceptado)
    if isinstance(response_text, dict):
        visual_package = response_text
        # Fallback de seguridad
        if "response_type" not in visual_package:
            visual_package["response_type"] = "visual_package"
        if "content" not in visual_package:
             visual_package["content"] = []
    
    else:
        # Caso Legacy/LLM: El Router devolvió un String (Texto o Markdown)
        import re
        import json
        
        # DEFINICIÓN CRÍTICA: Asegurar que clean_text existe para el regex
        clean_text = str(response_text)
        
        # 1. Intentar parsear si el agente respondió con JSON nativo (o lo empaquetó en markdown)
        # Usamos un regex más flexible para capturar el primer objeto JSON encontrado
        json_match = re.search(r"(\{.*?\})", clean_text, re.DOTALL)
        if json_match:
            try:
                candidate = json.loads(json_match.group(1))
                if isinstance(candidate, dict):
                    # Si tiene 'content', es el formato estándar
                    if "content" in candidate:
                        visual_package = candidate
                    
                    if visual_package and "response_type" not in visual_package:
                        visual_package["response_type"] = "visual_package"
            except json.JSONDecodeError:
                pass
            
        # 2. Fallback: Si no pudimos parsear JSON, envolvemos el texto plano
        if not visual_package:
            visual_package = {
                "response_type": "visual_package",
                "content": [{"type": "text", "payload": response_text}]
            }

    final_response_text = ""
    if isinstance(response_text, dict):
        # Usar el summary del paquete si existe, sino un default
        final_response_text = response_text.get("summary", "Se han generado datos visuales.")
    else:
        final_response_text = response_text

    # SENSOR VISUAL: Imprimir el contrato JSON saliente para debug
    if visual_package:
        print("\n🔍 [SENSOR VISUAL] Outgoing JSON Payload:")
        print(json.dumps(visual_package, indent=2, default=str))
        print("-" * 60)

    return ChatResponse(
        response=final_response_text, 
        response_type=visual_package["response_type"],
        content=visual_package["content"],
        session_id=request.session_id,
        metadata={"agent_name": ai_router.name}
    )

@api_router.post("/session/reset")
async def reset_session(request: ResetSessionRequest, current_user: TokenData = Depends(get_current_user)):
    """
    Endpoint para borrar la memoria (sesión) del agente.
    Permite al usuario iniciar una conversación limpia.
    """
    try:
        service = get_firestore_service()
        doc_ref = service.client.collection(settings.FIRESTORE_COLLECTION).document(request.session_id)
        
        # Eliminar documento (Firestore API)
        await doc_ref.delete()
        
        return {"status": "success", "message": f"Sesión {request.session_id} eliminada exitosamente."}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar sesión: {str(e)}"
        )

# --- Endpoints de Prueba de Infraestructura (Mock) ---

@api_router.get("/test/bigquery")
async def test_bigquery():
    try:
        bq = get_bq_service()
        # Consulta de validación simple
        query = "SELECT 1 as connection_test"
        df = bq.execute_query(query)
        return {"status": "success", "data": df.to_dict(orient="records")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@api_router.get("/test/storage")
async def test_storage():
    try:
        storage_svc = get_storage_service()
        settings = get_settings()
        bucket = storage_svc.client.bucket(settings.GCS_BUCKET_DOCS)
        blobs = list(bucket.list_blobs(max_results=5))
        return {
            "status": "success", 
            "bucket": settings.GCS_BUCKET_DOCS,
            "files": [b.name for b in blobs]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@api_router.get("/test/firestore")
async def test_firestore():
    try:
        firestore_svc = get_firestore_service()
        test_id = "connection-test-id"
        test_data = {"test": True, "message": "Success"}
        
        await firestore_svc.save_session(test_id, test_data)
        retrieved = await firestore_svc.get_session(test_id)
        
        return {"status": "success", "saved": test_data, "retrieved": retrieved}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Force reload
