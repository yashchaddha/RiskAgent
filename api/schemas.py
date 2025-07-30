from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from models.models import UserStage, RiskStatus

# Authentication Schemas
class UserRegistrationRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    organization: str = Field(..., min_length=2, max_length=100)
    industry: str

class UserLoginRequest(BaseModel):
    name: str
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None
    token: Optional[str] = None

# Chat Schemas
class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    thread_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    success: bool
    message: str
    response: Optional[str] = None
    current_stage: Optional[UserStage] = None
    current_intent: Optional[str] = None
    popup_data: Optional[Dict[str, Any]] = None
    popup_type: Optional[str] = None
    awaiting_input: bool = False
    session_data: Optional[Dict[str, Any]] = None

class StreamChatResponse(BaseModel):
    type: str  # "message", "stage_update", "popup", "complete"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Risk Management Schemas
class RiskData(BaseModel):
    risk_id: Optional[str] = None
    description: str
    impact: str
    likelihood: str
    treatment_strategy: str
    treatment_measures: str
    # Additional fields for complete risk finalization
    asset_value: Optional[str] = None
    department: Optional[str] = None
    risk_owner: Optional[str] = None
    target_date: Optional[str] = None
    risk_progress: Optional[str] = None
    residual_exposure: Optional[str] = None
    selected: bool = False

class RiskSelectionRequest(BaseModel):
    selected_risk_ids: List[str]
    edited_risks: List[RiskData] = []
    thread_id: str

class RiskSelectionResponse(BaseModel):
    success: bool
    message: str
    finalized_count: int
    current_stage: UserStage

class GenerateRisksRequest(BaseModel):
    thread_id: str
    additional_context: Optional[str] = ""

class ViewRisksResponse(BaseModel):
    success: bool
    risks: List[Dict[str, Any]]
    total_count: int
    risk_type: str  # "generated" or "finalized"

# Data Collection Schemas
class AdditionalRiskData(BaseModel):
    risk_id: str
    asset_value: Optional[str] = None
    department: Optional[str] = None
    risk_owner: Optional[str] = None
    target_date: Optional[str] = None
    risk_progress: Optional[str] = None
    residual_exposure: Optional[str] = None

class DataCollectionRequest(BaseModel):
    thread_id: str
    risks_data: List[AdditionalRiskData]

class DataCollectionResponse(BaseModel):
    success: bool
    message: str
    current_stage: UserStage
    awaiting_approval: bool = False

# Matrix Management Schemas
class MatrixUpdateRequest(BaseModel):
    matrix_size: str = Field(..., pattern="^(3x3|4x4|5x5)$")
    thread_id: str

class MatrixUpdateResponse(BaseModel):
    success: bool
    message: str
    new_likelihood_scale: List[str]
    new_impact_scale: List[str]
    matrix_size: str

# Report Management Schemas
class ReportApprovalRequest(BaseModel):
    thread_id: str
    approved: bool
    
class ReportApprovalResponse(BaseModel):
    success: bool
    message: str
    current_stage: UserStage
    report_id: Optional[str] = None

class ReportViewResponse(BaseModel):
    success: bool
    report: Optional[Dict[str, Any]] = None
    reports_list: Optional[List[Dict[str, Any]]] = None

# Session Management Schemas
class SessionStatusResponse(BaseModel):
    user_id: str
    current_stage: UserStage
    progress_summary: Dict[str, Any]
    session_active: bool
    last_activity: datetime

class WorkflowMetricsResponse(BaseModel):
    user_id: str
    organization: str
    industry: str
    completion_percentage: float
    steps_completed: int
    total_steps: int
    statistics: Dict[str, Any]
    step_details: Dict[str, bool]

# WebSocket Schemas
class WebSocketMessage(BaseModel):
    type: str  # "chat", "ping", "popup_interaction"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class WebSocketResponse(BaseModel):
    type: str  # "chat_response", "stage_update", "popup", "error", "pong"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Error Schemas
class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ValidationErrorResponse(BaseModel):
    success: bool = False
    error: str = "Validation error"
    validation_errors: List[Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Health Check Schemas
class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database_connected: bool
    llm_available: bool
    version: str = "1.0.0"

# Popup Interaction Schemas
class PopupInteractionRequest(BaseModel):
    thread_id: str
    popup_type: str
    action: str  # "submit", "cancel", "edit"
    data: Dict[str, Any]

class PopupInteractionResponse(BaseModel):
    success: bool
    message: str
    new_popup: Optional[Dict[str, Any]] = None
    current_stage: Optional[UserStage] = None
    redirect_to_chat: bool = False

# Bulk Operations Schemas
class BulkRiskUpdateRequest(BaseModel):
    thread_id: str
    risk_updates: List[Dict[str, Any]]

class BulkRiskUpdateResponse(BaseModel):
    success: bool
    message: str
    updated_count: int
    failed_updates: List[Dict[str, Any]] = []

# Search and Filter Schemas
class RiskSearchRequest(BaseModel):
    query: Optional[str] = None
    impact_filter: Optional[List[str]] = None
    likelihood_filter: Optional[List[str]] = None
    department_filter: Optional[List[str]] = None
    status_filter: Optional[List[RiskStatus]] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)

class RiskSearchResponse(BaseModel):
    success: bool
    risks: List[Dict[str, Any]]
    total_count: int
    filtered_count: int
    filters_applied: Dict[str, Any]

# Export Schemas
class ExportRequest(BaseModel):
    format: str = Field(..., pattern="^(pdf|excel|csv)$")
    include_reports: bool = True
    include_risks: bool = True
    date_range: Optional[Dict[str, str]] = None

class ExportResponse(BaseModel):
    success: bool
    download_url: Optional[str] = None
    file_id: Optional[str] = None
    expires_at: Optional[datetime] = None

# Validation Helpers
def validate_thread_id(cls, v):
    """Validate thread ID format"""
    if not v or not isinstance(v, str):
        raise ValueError("Thread ID is required")
    if not v.startswith("risk_agent_"):
        raise ValueError("Invalid thread ID format")
    return v

def validate_risk_data(cls, v):
    """Validate risk data structure"""
    required_fields = ["description", "impact", "likelihood", "treatment_strategy", "treatment_measures"]
    for field in required_fields:
        if field not in v or not v[field]:
            raise ValueError(f"Missing required field: {field}")
    return v

# Add validators to relevant schemas
# ChatMessageRequest.model_validate("thread_id")(validate_thread_id)
# RiskSelectionRequest.model_validate("thread_id")(validate_thread_id)
# GenerateRisksRequest.model_validate("thread_id")(validate_thread_id)
# DataCollectionRequest.model_validate("thread_id")(validate_thread_id)
# MatrixUpdateRequest.model_validate("thread_id")(validate_thread_id)
# ReportApprovalRequest.model_validate("thread_id")(validate_thread_id)
# PopupInteractionRequest.model_validate("thread_id")(validate_thread_id)

# Response Models Union Types
APIResponse = Union[
    ChatMessageResponse,
    AuthResponse,
    RiskSelectionResponse,
    DataCollectionResponse,
    MatrixUpdateResponse,
    ReportApprovalResponse,
    ErrorResponse
]

# Request Models Union Types  
APIRequest = Union[
    ChatMessageRequest,
    UserRegistrationRequest,
    UserLoginRequest,
    RiskSelectionRequest,
    GenerateRisksRequest,
    DataCollectionRequest,
    MatrixUpdateRequest,
    ReportApprovalRequest,
    PopupInteractionRequest
]