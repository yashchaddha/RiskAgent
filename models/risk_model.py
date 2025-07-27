from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from models.user_model import PyObjectId

class RiskValueWeight(BaseModel):
    value: str
    weight: int

class CreatedBy(BaseModel):
    name: str
    email: Optional[str] = None
    user_id: PyObjectId

class Approver(BaseModel):
    name: str
    user_id: PyObjectId
    approved_at: datetime = Field(default_factory=datetime.utcnow)

class IndividualRisk(BaseModel):
    risk_id: str = Field(..., description="Unique risk identifier (e.g., R-001)")
    risk_description: str = Field(..., min_length=10, max_length=500)
    likelihood: RiskValueWeight
    impact: RiskValueWeight
    treatment_strategy: str
    treatment_measures: str = Field(..., min_length=10, max_length=1000)
    
    # Metadata fields (collected post-approval)
    asset_value: Optional[float] = None
    department: Optional[str] = None
    risk_owner: Optional[str] = None
    target_date: Optional[datetime] = None
    risk_progress: Optional[str] = "Not Started"
    residual_exposure: Optional[RiskValueWeight] = None
    
    # Calculated fields
    inherent_risk_score: Optional[int] = None
    residual_risk_score: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class WeightMapping(BaseModel):
    very_low: RiskValueWeight = RiskValueWeight(value="Very Low", weight=1)
    low: RiskValueWeight = RiskValueWeight(value="Low", weight=2)
    medium: RiskValueWeight = RiskValueWeight(value="Medium", weight=3)
    high: RiskValueWeight = RiskValueWeight(value="High", weight=4)
    very_high: RiskValueWeight = RiskValueWeight(value="Very High", weight=5)

class RiskRegister(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    title: str = Field(..., min_length=5, max_length=200)
    organization: str
    created_by: CreatedBy
    approvers: List[Approver] = []
    risks: List[IndividualRisk] = []
    
    # Metadata
    total_risks: int = 0
    approved_risks: int = 0
    status: str = "Draft"  # Draft, In Review, Approved, Published
    version: str = "1.0"
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    
    # Optimistic locking
    version_id: int = 1

    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class RiskCreateRequest(BaseModel):
    risk_description: str
    likelihood: str
    impact: str  
    treatment_strategy: str
    treatment_measures: str

class RiskUpdateRequest(BaseModel):
    risk_id: str
    field: str
    value: Any
