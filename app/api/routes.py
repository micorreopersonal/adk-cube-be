from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import get_settings
from app.schemas.chat import ChatRequest, ChatResponse, Token, TokenData
from app.core.security import create_access_token, get_current_user
from app.core.mock_users import get_user
# Note: This import will be updated in Phase 6, but putting correct one now
from app.ai.agents.router_logic import get_router 
from app.services.bigquery import get_bq_service
from app.services.storage import get_storage_service
from app.services.firestore import get_firestore_service

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
    # Validación contra "Base de Datos" de Mock Users
    user_db = get_user(form_data.username)
    
    if not user_db or user_db["password"] != form_data.password:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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
    from app.ai.utils.response_builder import ResponseBuilder
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
                    # Si tiene 'visual_package', es el formato detectado en el error (resiliencia)
                    elif "visual_package" in candidate:
                        nested = candidate["visual_package"]
                        builder = ResponseBuilder()
                        if isinstance(nested, dict):
                            if "text" in nested: builder.add_text(nested["text"])
                        elif isinstance(nested, str):
                            builder.add_text(nested)
                        visual_package = builder.to_dict()
                    
                    if visual_package and "response_type" not in visual_package:
                        visual_package["response_type"] = "visual_package"
            except json.JSONDecodeError:
                pass
            
        # 2. Fallback: Si no pudimos parsear JSON, envolvemos el texto plano
        if not visual_package:
            builder = ResponseBuilder()
            builder.add_text(response_text)
            visual_package = builder.to_dict()

    # Determinar el texto de respuesta (Legacy support)
    final_response_text = ""
    if isinstance(response_text, dict):
        # Intentar extraer texto del payload si existe
        if "content" in response_text:
             for block in response_text["content"]:
                 if block["type"] == "text":
                     final_response_text += block["payload"] + "\n"
        
        if not final_response_text:
            final_response_text = "Se han generado datos visuales. Revisa el componente interactivo."
    else:
        final_response_text = response_text

    return ChatResponse(
        response=final_response_text, 
        response_type=visual_package["response_type"],
        content=visual_package["content"],
        session_id=request.session_id,
        metadata={"agent_name": ai_router.name}
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
