from typing import List, Dict, Any
from datetime import datetime
from models.risk_model import IndividualRisk, RiskValueWeight, RiskRegister, CreatedBy
from database.repository import risk_register_repository
from config.constants import LIKELIHOOD_VALUES, IMPACT_VALUES, DEFAULT_ORG_CONTEXT
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

async def save_risk_register(username: str, session_data: dict):
    # Build the official RiskRegister using your unchangeable models
    db_risks = []
    for draft in session_data["draft_risks"]:
        db_risks.append(
            IndividualRisk(
                risk_id=draft["risk_id"],
                risk_description=draft["risk_description"],
                likelihood=RiskValueWeight(**draft["likelihood"]),
                impact=RiskValueWeight(**draft["impact"]),
                treatment_strategy=draft["treatment_strategy"],
                treatment_measures=draft["treatment_measures"],
                # metadata fields set later
            )
        )

    register = RiskRegister(
        title=session_data.get("register_title", "Default Title"),
        organization=session_data["organization"],
        created_by=CreatedBy(
            name=username,
            email=session_data.get("user_email"),
            user_id=session_data["user_id"]
        ),
        risks=db_risks,
        total_risks=len(db_risks),
        status="Approved",
    )
    # persist via your repository
    await risk_register_repository.create_risk_register(register)

def validate_risk_data(risk_data: Dict[str, Any]) -> bool:
    """Validate risk data structure"""
    required_fields = [
        "risk_description", "likelihood", "impact", 
        "treatment_strategy", "treatment_measures"
    ]
    
    for field in required_fields:
        if field not in risk_data or not risk_data[field]:
            return False
            
    # Validate likelihood and impact values
    if risk_data["likelihood"] not in LIKELIHOOD_VALUES:
        return False
    if risk_data["impact"] not in IMPACT_VALUES:
        return False
        
    return True

def update_risk_field(risk: IndividualRisk, field: str, value: Any) -> IndividualRisk:
    """Update a specific field of a risk"""
    try:
        if field == "likelihood":
            if value in LIKELIHOOD_VALUES:
                risk.likelihood = RiskValueWeight(
                    value=value,
                    weight=LIKELIHOOD_VALUES[value]
                )
                # Recalculate risk score
                risk.inherent_risk_score = risk.likelihood.weight * risk.impact.weight
        elif field == "impact":
            if value in IMPACT_VALUES:
                risk.impact = RiskValueWeight(
                    value=value,
                    weight=IMPACT_VALUES[value]
                )
                # Recalculate risk score
                risk.inherent_risk_score = risk.likelihood.weight * risk.impact.weight
        elif field == "residual_exposure":
            if isinstance(value, dict) and "value" in value and "weight" in value:
                risk.residual_exposure = RiskValueWeight(
                    value=value["value"],
                    weight=value["weight"]
                )
                risk.residual_risk_score = risk.residual_exposure.weight
        elif hasattr(risk, field):
            setattr(risk, field, value)
        else:
            raise ValueError(f"Invalid field: {field}")
            
        risk.updated_at = datetime.utcnow()
        return risk
        
    except Exception as e:
        logger.error(f"Error updating risk field {field}: {e}")
        raise
