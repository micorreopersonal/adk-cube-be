from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.routes import api_router

settings = get_settings()

app = FastAPI(
    title="ADK Talent Analytics API",
    description="API para el ecosistema multi-agente de People Analytics (SOTA 2026)",
    version="2.0.0"
)

# Configuración de CORS
# TODO: Restringir orígenes en producción real cuando tengamos frontend definitivo
origins = ["*"] #if settings.ENV in ["development", "test"] else ["https://tu-frontend-prod.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas aisladas
app.include_router(api_router)
