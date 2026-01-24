from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class ChatRequest(BaseModel):
    message: str = Field(..., description="El mensaje del usuario.")
    session_id: str = Field(..., description="ID único de sesión.")
    context_profile: Optional[str] = Field(None, description="Perfil opcional para ajustar instrucciones.")

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    profile: Optional[str] = "EJECUTIVO"
