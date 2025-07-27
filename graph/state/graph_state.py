from pydantic import BaseModel, Field
from typing import Any, Dict
from datetime import datetime
from bson import ObjectId
from typing import List, Optional, Dict, Any
from models.risk_model import IndividualRisk
from models.user_model import PyObjectId

# Unified GraphState for Langraph execution and persistence
def str_objid(v: Any) -> str:
    return str(v) if isinstance(v, ObjectId) else v

class GraphState(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: Optional[PyObjectId] = None
    username: str
    user_message: str = ""
    session_id: str = ""
    current_node: str = "auth"
    intent: str = ""
    response: str = ""
    requires_input: bool = False
    error: str = ""
    draft_risks: List[Dict[str, Any]] = Field(default_factory=list)  # Changed to list of dicts
    selected_risk_ids: List[str] = Field(default_factory=list)
    risk_register_id: Optional[PyObjectId] = None
    risks_approved: bool = False
    approval_timestamp: Optional[datetime] = None
    show_risks: bool = False  # Frontend flag to display risks UI
    show_metadata_popup: bool = False  # Frontend flag to display metadata collection popup
    metadata_completed: bool = False  # Flag to track if metadata has been completed
    # Additional fields used by nodes
    metadata_pending: List[Dict[str, Any]] = Field(default_factory=list)
    metadata_results: List[Dict[str, Any]] = Field(default_factory=list)
    authenticated: bool = False
    resume_node: str = "auth"
    is_active: bool = True
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Legacy session_data field for backward compatibility with existing nodes
    session_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str_objid}   