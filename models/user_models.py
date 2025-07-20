from pydantic import BaseModel, Field
from uuid import uuid4

class User(BaseModel):
    """Simple user model"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    username: str
    
    class Config:
        populate_by_name = True