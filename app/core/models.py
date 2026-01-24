from pydantic import BaseModel
from typing import Optional, List, Any

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    user_context: Optional[dict] = {}

class ChatResponse(BaseModel):
    response: str
    agent_name: str
    metadata: Optional[dict] = {}
