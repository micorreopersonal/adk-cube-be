from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.models import ChatRequest, ChatResponse
from app.agents.router import get_router
from app.services.bigquery import get_bq_service
from app.services.storage import get_storage_service
from app.services.firestore import get_firestore_service

settings = get_settings()
router = get_router()

app = FastAPI(
    title="ADK Talent Analytics API",
    description="API para el ecosistema multi-agente de People Analytics",
    version="0.1.0"
)

# Configuración de CORS
origins = ["*"] if settings.ENV == "development" else ["https://tu-frontend-prod.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "ADK Talent Analytics API is running",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal para interactuar con el ecosistema de agentes.
    """
    response_text = await router.route(request.message)
    
    return ChatResponse(
        response=response_text,
        agent_name=router.name,
        metadata={"session_id": request.session_id}
    )

# --- Endpoints de Prueba de Infraestructura (Mock) ---

@app.get("/test/bigquery")
async def test_bigquery():
    try:
        bq = get_bq_service()
        # Consulta de validación simple
        query = "SELECT 1 as connection_test"
        df = bq.execute_query(query)
        return {"status": "success", "data": df.to_dict(orient="records")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/test/storage")
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

@app.get("/test/firestore")
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
