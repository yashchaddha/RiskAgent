from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    username: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatResponse(BaseModel):
    response: str
    session_id: str
    current_node: str
    intent: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    requires_input: bool = False