import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt  # PyJWT Migration
from passlib.context import CryptContext

from app.core.config.config import get_settings
from app.schemas.chat import TokenData
from app.core.config.constants import ProfileEnum

settings = get_settings()

# Configuración desde settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 día

# Token maestro para desarrollo (solo activo en modo test/development)
DEV_TOKEN_MOCK = "dev-token-mock"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Usar la constante configurada (1 día) en lugar del hardcode de 15 min
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 🛡️ BYPASS MODO DESARROLLO (Solo si APP_ENV es 'test' o 'development')
    if settings.APP_ENV in ["test", "development"] and token == DEV_TOKEN_MOCK:
        # En desarrollo, el mock devuelve perfil ADMIN por defecto para pruebas totales
        return TokenData(username="developer-admin", profile="ADMIN")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        # Default a Ejecutivo si no viene en token
        profile: str = payload.get("profile", ProfileEnum.EJECUTIVO.value) 
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, profile=profile)
    except jwt.PyJWTError:  # Updated from jose.JWTError
        raise credentials_exception
    return token_data

# --- FUNCIONES DE ANONIMIZACIÓN EXISTENTES ---

def mask_document_id(doc_id: str) -> str:
    """
    Anonimiza un documento de identidad peruano:
    - DNI (8 dígitos): 12345678 -> 12.***.**8
    - CE (9-12 chars): 001234567 -> 00.***.**7
    """
    if not doc_id:
        return doc_id
    
    # Limpieza básica
    clean_doc = doc_id.replace(" ", "").replace("-", "").replace(".", "")
    
    # Lógica DNI (8 dígitos)
    if len(clean_doc) == 8 and clean_doc.isdigit():
        return f"{clean_doc[:2]}.***.**{clean_doc[-1]}"
        
    # Lógica CE (Generalmente 9, pero puede variar)
    if len(clean_doc) >= 9:
        return f"{clean_doc[:2]}.***.**{clean_doc[-1]}"
        
    # Fallback
    return "XX.XXX.XXX"

def mask_salary(salary: float) -> str:
    """
    Anonimiza un salario monetario.
    Regla Global: Los salarios deben ser ocultados en logs.
    """
    return "[SALARIO_CONFIDENCIAL]"

def clean_sensitive_data(text: str) -> str:
    """
    Busca patrones de DNI/CE en un texto y los enmascara.
    Regex orientada a 8 dígitos seguidos (DNI común).
    """
    # Regex para DNI (8 dígitos aislados o con separadores)
    dni_pattern = r'\b\d{2}[\.\-]?\d{3}[\.\-]?\d{3}\b'
    # Regex para CE (aprox - Alfanumérico 9 chars)
    ce_pattern = r'\b[0-9]{9,12}\b'
    
    text = re.sub(dni_pattern, "XX.XXX.XXX", text)
    text = re.sub(ce_pattern, "XX.XXX.XXX", text)
    return text
