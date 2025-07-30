from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class UserStage(str, Enum):
    WELCOME = "welcome"
    RISK_GENERATION = "risk_generation"
    RISK_EDITING = "risk_editing"
    DATA_COLLECTION = "data_collection"
    AWAITING_REPORT_APPROVAL = "awaiting_report_approval"
    REPORT_READY = "report_ready"

class RiskStatus(str, Enum):
    GENERATED = "generated"
    FINALIZED = "finalized"

class User(BaseModel):
    user_id: Optional[str] = None
    name: str
    password: str
    organization: str
    industry: str
    likelihood_scale: List[str] = Field(default=["Low", "Medium", "High"])
    impact_scale: List[str] = Field(default=["Low", "Medium", "High"])
    current_stage: UserStage = UserStage.WELCOME
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserLogin(BaseModel):
    name: str
    password: str

class UserRegistration(BaseModel):
    name: str
    password: str
    organization: str
    industry: str

class GeneratedRisk(BaseModel):
    risk_id: Optional[str] = None
    user_id: str
    description: str
    impact: str
    likelihood: str
    treatment_strategy: str
    treatment_measures: str
    status: RiskStatus = RiskStatus.GENERATED
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FinalizedRisk(BaseModel):
    risk_id: Optional[str] = None
    user_id: str
    description: str
    impact: str
    likelihood: str
    treatment_strategy: str
    treatment_measures: str
    # Additional data fields
    asset_value: Optional[str] = None
    department: Optional[str] = None
    risk_owner: Optional[str] = None
    target_date: Optional[datetime] = None
    risk_progress: Optional[str] = None
    residual_exposure: Optional[str] = None
    status: RiskStatus = RiskStatus.FINALIZED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RiskSelectionRequest(BaseModel):
    selected_risk_ids: List[str]
    edited_risks: List[GeneratedRisk] = []

class AdditionalDataRequest(BaseModel):
    risks_data: List[dict]  # List of risk updates with additional fields

class MatrixUpdateRequest(BaseModel):
    matrix_size: str  # "3x3", "4x4", "5x5"

class RiskReport(BaseModel):
    report_id: Optional[str] = None
    user_id: str
    organization: str
    industry: str
    total_risks: int
    high_priority_risks: int
    report_content: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)

# LangGraph State Model
class RiskAgentState(BaseModel):
    user_id: str
    current_stage: UserStage
    current_intent: Optional[str] = None
    pending_popup: Optional[dict] = None
    session_context: Optional[str] = None