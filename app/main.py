from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config.config import get_settings
from app.api.routes import api_router
import logging
import sys
import os
from datetime import datetime

# Persistent debug file for catching "0%" bug
DEBUG_FILE = "c:/adk-projects/adk-people-analytics-backend/test_debug.log"

def log_debug(msg: str):
    try:
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            f.write(f"[{timestamp}] MAIN: {msg}\n")
    except Exception as e:
        print(f"FAILED TO WRITE LOG IN MAIN: {e}", flush=True)
    print(msg, flush=True)

log_debug(f"🚀 API Entrypoint main.py loaded. CWD: {os.getcwd()}")

try:
    import app.ai.tools.executive_report_stream as ers
    log_debug(f"🚀 executive_report_stream loaded from: {ers.__file__}")
except Exception as e:
    log_debug(f"❌ Failed to import ers: {e}")

settings = get_settings()

# Configuración de Logging Global
# Force Logger Level (Uvicorn overrides basicConfig)
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

# Ensure we have a handler to stdout
if not root_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(handler)

logger = logging.getLogger(__name__)
logger.info(f"🚀 Iniciando ADK Talent Analytics API en modo {settings.ENV}")

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
app.include_router(api_router, prefix="/api")
