from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class ChatRequest(BaseModel):
    message: str = Field(..., description="El mensaje del usuario.")
    session_id: str = Field(..., description="ID único de sesión.")
    context_profile: Optional[str] = Field(None, description="Perfil opcional para ajustar instrucciones.")

class ChatResponse(BaseModel):
    response: Optional[str] = None # Deprecated but kept for compatibility
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None
    
    # New Fields for VisualDataPackage
    response_type: str = Field("text", description="Type of response: 'text' or 'visual_package'")
    content: Optional[List[dict]] = Field(None, description="List of visual blocks (text, kpi_row, plot, table)")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    profile: Optional[str] = "EJECUTIVO"

class ResetSessionRequest(BaseModel):
    session_id: str = Field(..., description="ID de sesión a limpiar.")
