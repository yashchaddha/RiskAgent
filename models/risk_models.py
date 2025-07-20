# models/risk_models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from uuid import uuid4

class WeightedValue(BaseModel):
    value: str
    weight: float

class RiskItem(BaseModel):
    risk_id: str = Field(default_factory=lambda: str(uuid4()))
    username: str
    risk_description: str
    category: List[str] = Field(default_factory=list)
    likelihood: WeightedValue
    impact: WeightedValue
    exposure: WeightedValue
    
    department: str
    asset_value: str
    risk_owner: str
    risk_treatment_strategy: str
    target_date: Optional[datetime] = None
    risk_treatment_measures: str
    risk_progress: str = ""
    residual_exposure: str = ""
    
    is_approved: bool = False
    status: Literal["draft", "approved", "rejected"] = "draft"
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True

def create_weighted_value(value: str, weight: float = 1.0) -> WeightedValue:
    """Helper to create weighted values"""
    return WeightedValue(value=value, weight=weight)

def create_basic_risk(
    username: str,
    description: str,
    category: List[str],
    likelihood_value: str = "Medium",
    impact_value: str = "Medium",
    exposure_value: str = "Medium",
    department: str = "IT",
    asset_value: str = "High",
    risk_owner: str = "IT Manager",
    treatment_strategy: str = "Mitigate",
    treatment_measures: str = "Implement controls"
) -> RiskItem:
    """Helper to create a basic risk with default values"""
    return RiskItem(
        username=username,
        risk_description=description,
        category=category,
        likelihood=create_weighted_value(likelihood_value, 2.0),
        impact=create_weighted_value(impact_value, 2.0),
        exposure=create_weighted_value(exposure_value, 2.0),
        department=department,
        asset_value=asset_value,
        risk_owner=risk_owner,
        risk_treatment_strategy=treatment_strategy,
        risk_treatment_measures=treatment_measures
    )