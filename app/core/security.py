import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt  # PyJWT Migration
from passlib.context import CryptContext

from app.core.config import get_settings
from app.schemas.chat import TokenData
from app.core.constants import ProfileEnum

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
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
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

def mask_rut(rut: str) -> str:
    """
    Anonimiza un RUT chileno (ej: 12.345.678-9 -> 12.XXX.XXX-X)
    """
    if not rut:
        return rut
    
    # Separar cuerpo y dígito verificador si es posible
    parts = re.split(r'[-]', rut)
    body = parts[0]
    
    if len(body) > 4:
        masked_body = body[:2] + "." + "X" * 3 + "." + "X" * 3
        if len(parts) > 1:
            return f"{masked_body}-X"
        return masked_body
    return "X.XXX.XXX-X"

def mask_salary(salary: float) -> str:
    """
    Anonimiza un salario convirtiéndolo en un rango o simplemente enmascarándolo.
    Según GLOBAL_RULES, los salarios deben ser anonimizados en los logs.
    """
    return "[SALARIO_CONFIDENCIAL]"

def clean_sensitive_data(text: str) -> str:
    """
    Busca patrones de RUT en un texto y los enmascara.
    """
    # Regex simple para RUT
    rut_pattern = r'\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]'
    return re.sub(rut_pattern, "XX.XXX.XXX-X", text)
