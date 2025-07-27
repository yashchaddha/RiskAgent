from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from bson import ObjectId
from models.risk_model import RiskRegister, IndividualRisk, RiskCreateRequest, RiskUpdateRequest
from database.repository import risk_register_repository
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/risks/registers", response_model=List[dict])
async def get_risk_registers(user_id: str = Query(..., description="User ID")):
    """Get all risk registers for a user"""
    try:
        registers = await risk_register_repository.get_risk_registers_by_user(ObjectId(user_id))
        return [
            {
                "id": str(register.id),
                "title": register.title,
                "organization": register.organization,
                "status": register.status,
                "total_risks": register.total_risks,
                "created_at": register.created_at,
                "updated_at": register.updated_at
            }
            for register in registers
        ]
    except Exception as e:
        logger.error(f"Error getting risk registers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/risks/register/{register_id}", response_model=dict)
async def get_risk_register(register_id: str):
    """Get a specific risk register"""
    try:
        register = await risk_register_repository.get_risk_register_by_id(ObjectId(register_id))
        if not register:
            raise HTTPException(status_code=404, detail="Risk register not found")
            
        return register.dict()
    except Exception as e:
        logger.error(f"Error getting risk register: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/risks/register/{register_id}/risk")
async def add_risk_to_register(register_id: str, risk: RiskCreateRequest):
    """Add a new risk to a register"""
    try:
        register = await risk_register_repository.get_risk_register_by_id(ObjectId(register_id))
        if not register:
            raise HTTPException(status_code=404, detail="Risk register not found")
            
        # Create new risk
        from config.constants import LIKELIHOOD_VALUES, IMPACT_VALUES
        from models.risk_model import RiskValueWeight
        
        new_risk = IndividualRisk(
            risk_id=f"R-{len(register.risks) + 1:03d}",
            risk_description=risk.risk_description,
            likelihood=RiskValueWeight(
                value=risk.likelihood,
                weight=LIKELIHOOD_VALUES[risk.likelihood]
            ),
            impact=RiskValueWeight(
                value=risk.impact,
                weight=IMPACT_VALUES[risk.impact]
            ),
            treatment_strategy=risk.treatment_strategy,
            treatment_measures=risk.treatment_measures
        )
        
        # Calculate inherent risk score
        new_risk.inherent_risk_score = new_risk.likelihood.weight * new_risk.impact.weight
        
        # Add to register
        register.risks.append(new_risk)
        register.total_risks = len(register.risks)
        
        # Save
        success = await risk_register_repository.update_risk_register(register)
        if not success:
            raise HTTPException(status_code=409, detail="Conflict updating register")
            
        return {"message": "Risk added successfully", "risk_id": new_risk.risk_id}
        
    except Exception as e:
        logger.error(f"Error adding risk: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/risks/register/{register_id}/risk/{risk_id}")
async def update_risk(register_id: str, risk_id: str, update: RiskUpdateRequest):
    """Update a specific risk in a register"""
    try:
        register = await risk_register_repository.get_risk_register_by_id(ObjectId(register_id))
        if not register:
            raise HTTPException(status_code=404, detail="Risk register not found")
            
        # Find the risk
        risk_found = False
        for risk in register.risks:
            if risk.risk_id == risk_id:
                # Update the field
                if hasattr(risk, update.field):
                    setattr(risk, update.field, update.value)
                    risk_found = True
                    break
                else:
                    raise HTTPException(status_code=400, detail=f"Invalid field: {update.field}")
        
        if not risk_found:
            raise HTTPException(status_code=404, detail="Risk not found")
            
        # Save
        success = await risk_register_repository.update_risk_register(register)
        if not success:
            raise HTTPException(status_code=409, detail="Conflict updating register")
            
        return {"message": "Risk updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating risk: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/risks/register/{register_id}/risk/{risk_id}")
async def delete_risk(register_id: str, risk_id: str):
    """Delete a risk from a register"""
    try:
        register = await risk_register_repository.get_risk_register_by_id(ObjectId(register_id))
        if not register:
            raise HTTPException(status_code=404, detail="Risk register not found")
            
        # Remove the risk
        initial_count = len(register.risks)
        register.risks = [risk for risk in register.risks if risk.risk_id != risk_id]
        
        if len(register.risks) == initial_count:
            raise HTTPException(status_code=404, detail="Risk not found")
            
        register.total_risks = len(register.risks)
        
        # Save
        success = await risk_register_repository.update_risk_register(register)
        if not success:
            raise HTTPException(status_code=409, detail="Conflict updating register")
            
        return {"message": "Risk deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting risk: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
