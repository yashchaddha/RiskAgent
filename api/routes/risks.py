from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from langchain_core.messages import HumanMessage

from api.schemas import (
    GenerateRisksRequest, RiskSelectionRequest, RiskSelectionResponse,
    ViewRisksResponse, DataCollectionRequest, DataCollectionResponse,
    RiskSearchRequest, RiskSearchResponse, BulkRiskUpdateRequest, BulkRiskUpdateResponse
)
from api.auth import get_current_user, validate_session_access
from graph import invoke_risk_workflow, get_workflow_state, update_workflow_state
from database.repository import repo_factory
from models.models import User, RiskStatus, UserStage
from config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/risks", tags=["risk_management"])

@router.post("/generate")
async def generate_risks(
    request: GenerateRisksRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate new risks for the user's organization
    """
    
    logger.info(f"Risk generation request from user {current_user.user_id}")
    
    try:
        # Validate thread access
        if not await validate_session_access(current_user.user_id, request.thread_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid thread access"
            )
        
        # Get current workflow state
        current_state = await get_workflow_state(request.thread_id)
        
        if not current_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Prepare message for risk generation
        message_content = "Generate risks for my organization"
        if request.additional_context:
            message_content += f". Additional context: {request.additional_context}"
        
        # Add user message and set intent
        messages = current_state.get("messages", [])
        messages.append(HumanMessage(content=message_content))
        
        current_state["messages"] = messages
        current_state["current_intent"] = "generate_risks"
        
        # Invoke workflow for risk generation
        result = await invoke_risk_workflow(current_state, request.thread_id)
        
        # Check for popup data (generated risks)
        popup_data = result.get("pending_popup")
        popup_type = result.get("popup_type")
        
        if popup_type == "risk_selection" and popup_data:
            risks = popup_data.get("risks", [])
            total_generated = popup_data.get("total_generated", len(risks))
            
            logger.info(f"Generated {total_generated} risks for user {current_user.user_id}")
            
            return {
                "success": True,
                "message": f"Generated {total_generated} risks successfully",
                "risks": risks,
                "total_generated": total_generated,
                "popup_data": popup_data,
                "current_stage": result.get("current_stage")
            }
        else:
            # Check for error or fallback response
            messages = result.get("messages", [])
            response_content = ""
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, 'content'):
                    response_content = last_msg.content
            
            return {
                "success": False,
                "message": "Risk generation failed",
                "response": response_content,
                "current_stage": result.get("current_stage")
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk generation error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate risks"
        )

@router.post("/finalize", response_model=RiskSelectionResponse)
async def finalize_risks(
    request: RiskSelectionRequest,
    current_user: User = Depends(get_current_user)
) -> RiskSelectionResponse:
    """
    Finalize selected risks with complete data directly (combined finalization + data collection)
    """
    
    logger.info(f"Complete risk finalization request from user {current_user.user_id}: {len(request.edited_risks)} risks")
    
    try:
        # Validate thread access
        if not await validate_session_access(current_user.user_id, request.thread_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid thread access"
            )
        
        if not request.edited_risks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No risk data provided for finalization"
            )
        
        # Use the new complete finalization method
        risk_repo = repo_factory.risk_repository
        
        # Prepare risk data for complete finalization
        risk_data_list = []
        for risk in request.edited_risks:
            risk_dict = risk.dict()
            # Remove fields that shouldn't be in the database
            risk_dict.pop('selected', None)
            risk_dict.pop('risk_id', None)  # Will be generated by database
            risk_data_list.append(risk_dict)
        
        # Finalize risks with complete data in one step
        finalized_ids = await risk_repo.finalize_risks_with_complete_data(
            risk_data_list, 
            current_user.user_id
        )
        
        if not finalized_ids:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to finalize any risks"
            )
        
        # Update workflow state to reflect completion
        await update_workflow_state(request.thread_id, {
            "current_stage": UserStage.RISK_EDITING,  # Stay in editing mode for potential additional actions
            "popup_type": None,
            "pending_popup": None,
            "temp_data": {
                "finalized_risk_ids": finalized_ids,
                "total_risks_finalized": len(finalized_ids)
            }
        })
        
        # Get updated finalized count
        finalized_count = await risk_repo.get_finalized_risks_count(current_user.user_id)
        
        logger.info(f"Successfully finalized {len(finalized_ids)} complete risks for user {current_user.user_id}")
        
        return RiskSelectionResponse(
            success=True,
            message=f"Successfully finalized {len(finalized_ids)} risks with complete information. You can now generate more risks or proceed to report generation.",
            finalized_count=finalized_count,
            current_stage=UserStage.RISK_EDITING
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Complete risk finalization error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to finalize risks with complete data"
        )

@router.get("/view", response_model=ViewRisksResponse)
async def view_risks(
    current_user: User = Depends(get_current_user),
    risk_type: str = Query("finalized", regex="^(generated|finalized)$"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
) -> ViewRisksResponse:
    """
    View user's risks (generated or finalized)
    """
    
    logger.info(f"View risks request from user {current_user.user_id}: type={risk_type}")
    
    try:
        risk_repo = repo_factory.risk_repository
        
        if risk_type == "finalized":
            # Get finalized risks
            risks = await risk_repo.get_finalized_risks_by_user(current_user.user_id)
            
            # Format for response
            formatted_risks = [
                {
                    "risk_id": risk.risk_id,
                    "description": risk.description,
                    "impact": risk.impact,
                    "likelihood": risk.likelihood,
                    "treatment_strategy": risk.treatment_strategy,
                    "treatment_measures": risk.treatment_measures,
                    "asset_value": risk.asset_value,
                    "department": risk.department,
                    "risk_owner": risk.risk_owner,
                    "target_date": risk.target_date.isoformat() if risk.target_date else None,
                    "risk_progress": risk.risk_progress,
                    "residual_exposure": risk.residual_exposure,
                    "status": risk.status,
                    "created_at": risk.created_at.isoformat(),
                    "updated_at": risk.updated_at.isoformat() if risk.updated_at else None
                }
                for risk in risks[offset:offset+limit]
            ]
            
        else:  # generated
            # Get generated risks
            risks = await risk_repo.get_generated_risks_by_user(current_user.user_id)
            
            # Format for response
            formatted_risks = [
                {
                    "risk_id": risk.risk_id,
                    "description": risk.description,
                    "impact": risk.impact,
                    "likelihood": risk.likelihood,
                    "treatment_strategy": risk.treatment_strategy,
                    "treatment_measures": risk.treatment_measures,
                    "status": risk.status,
                    "created_at": risk.created_at.isoformat()
                }
                for risk in risks[offset:offset+limit]
            ]
        
        return ViewRisksResponse(
            success=True,
            risks=formatted_risks,
            total_count=len(risks),
            risk_type=risk_type
        )
        
    except Exception as e:
        logger.error(f"View risks error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve risks"
        )

@router.post("/data-collection", response_model=DataCollectionResponse)
async def submit_additional_data(
    request: DataCollectionRequest,
    current_user: User = Depends(get_current_user)
) -> DataCollectionResponse:
    """
    Submit additional data for finalized risks
    """
    
    logger.info(f"Data collection request from user {current_user.user_id}: {len(request.risks_data)} risks")
    
    try:
        # Validate thread access
        if not await validate_session_access(current_user.user_id, request.thread_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid thread access"
            )
        
        if not request.risks_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No risk data provided"
            )
        
        # Update workflow state with additional data
        await update_workflow_state(request.thread_id, {
            "temp_data": {
                "additional_data": [data.dict() for data in request.risks_data]
            },
            "current_intent": "fill_additional_data",
            "popup_type": None,
            "pending_popup": None
        })
        
        # Process data collection through workflow
        current_state = await get_workflow_state(request.thread_id)
        result = await invoke_risk_workflow(current_state, request.thread_id)
        
        logger.info(f"Additional data collected for {len(request.risks_data)} risks")
        
        return DataCollectionResponse(
            success=True,
            message=f"Successfully updated {len(request.risks_data)} risks with additional data",
            current_stage=result.get("current_stage"),
            awaiting_approval=result.get("awaiting_user_input", False)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data collection error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit additional data"
        )

@router.put("/update/{risk_id}")
async def update_risk(
    risk_id: str,
    risk_data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Update a specific risk
    """
    
    logger.info(f"Risk update request from user {current_user.user_id} for risk {risk_id}")
    
    try:
        risk_repo = repo_factory.risk_repository
        
        # Check if risk belongs to user (both generated and finalized)
        generated_risk = await risk_repo.get_generated_risk_by_id(risk_id)
        finalized_risk = await risk_repo.get_finalized_risk_by_id(risk_id)
        
        if not generated_risk and not finalized_risk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Risk not found"
            )
        
        # Verify ownership
        owner_user_id = generated_risk.user_id if generated_risk else finalized_risk.user_id
        if owner_user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this risk"
            )
        
        # Update the risk
        if generated_risk:
            success = await risk_repo.update_generated_risk(risk_id, risk_data)
        else:
            success = await risk_repo.update_finalized_risk_additional_data(risk_id, risk_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update risk"
            )
        
        return {
            "success": True,
            "message": "Risk updated successfully",
            "risk_id": risk_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk update error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update risk"
        )

@router.delete("/delete/{risk_id}")
async def delete_risk(
    risk_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a generated risk (only generated risks can be deleted)
    """
    
    logger.info(f"Risk deletion request from user {current_user.user_id} for risk {risk_id}")
    
    try:
        risk_repo = repo_factory.risk_repository
        
        # Check if risk exists and belongs to user
        risk = await risk_repo.get_generated_risk_by_id(risk_id)
        
        if not risk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generated risk not found"
            )
        
        if risk.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this risk"
            )
        
        # Delete the risk
        success = await risk_repo.delete_generated_risk(risk_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete risk"
            )
        
        return {
            "success": True,
            "message": "Risk deleted successfully",
            "risk_id": risk_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk deletion error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete risk"
        )

@router.post("/search", response_model=RiskSearchResponse)
async def search_risks(
    request: RiskSearchRequest,
    current_user: User = Depends(get_current_user)
) -> RiskSearchResponse:
    """
    Search and filter user's risks
    """
    
    logger.info(f"Risk search request from user {current_user.user_id}")
    
    try:
        risk_repo = repo_factory.risk_repository
        
        # Get all finalized risks for user
        all_risks = await risk_repo.get_finalized_risks_by_user(current_user.user_id)
        
        # Apply filters
        filtered_risks = all_risks
        
        # Text search filter
        if request.query:
            query_lower = request.query.lower()
            filtered_risks = [
                risk for risk in filtered_risks
                if query_lower in risk.description.lower() or
                   query_lower in (risk.treatment_strategy or "").lower() or
                   query_lower in (risk.department or "").lower()
            ]
        
        # Impact filter
        if request.impact_filter:
            filtered_risks = [
                risk for risk in filtered_risks
                if risk.impact in request.impact_filter
            ]
        
        # Likelihood filter
        if request.likelihood_filter:
            filtered_risks = [
                risk for risk in filtered_risks
                if risk.likelihood in request.likelihood_filter
            ]
        
        # Department filter
        if request.department_filter:
            filtered_risks = [
                risk for risk in filtered_risks
                if risk.department in request.department_filter
            ]
        
        # Status filter
        if request.status_filter:
            filtered_risks = [
                risk for risk in filtered_risks
                if risk.status in request.status_filter
            ]
        
        # Apply pagination
        total_filtered = len(filtered_risks)
        paginated_risks = filtered_risks[request.offset:request.offset + request.limit]
        
        # Format for response
        formatted_risks = [
            {
                "risk_id": risk.risk_id,
                "description": risk.description,
                "impact": risk.impact,
                "likelihood": risk.likelihood,
                "treatment_strategy": risk.treatment_strategy,
                "department": risk.department,
                "risk_owner": risk.risk_owner,
                "risk_progress": risk.risk_progress,
                "status": risk.status
            }
            for risk in paginated_risks
        ]
        
        return RiskSearchResponse(
            success=True,
            risks=formatted_risks,
            total_count=len(all_risks),
            filtered_count=total_filtered,
            filters_applied={
                "query": request.query,
                "impact_filter": request.impact_filter,
                "likelihood_filter": request.likelihood_filter,
                "department_filter": request.department_filter,
                "status_filter": request.status_filter
            }
        )
        
    except Exception as e:
        logger.error(f"Risk search error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search risks"
        )

@router.post("/bulk-update", response_model=BulkRiskUpdateResponse)
async def bulk_update_risks(
    request: BulkRiskUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> BulkRiskUpdateResponse:
    """
    Bulk update multiple risks
    """
    
    logger.info(f"Bulk risk update request from user {current_user.user_id}: {len(request.risk_updates)} risks")
    
    try:
        # Validate thread access
        if not await validate_session_access(current_user.user_id, request.thread_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid thread access"
            )
        
        risk_repo = repo_factory.risk_repository
        updated_count = 0
        failed_updates = []
        
        for update_data in request.risk_updates:
            try:
                risk_id = update_data.get("risk_id")
                if not risk_id:
                    failed_updates.append({"error": "Missing risk_id", "data": update_data})
                    continue
                
                # Check ownership
                finalized_risk = await risk_repo.get_finalized_risk_by_id(risk_id)
                if not finalized_risk or finalized_risk.user_id != current_user.user_id:
                    failed_updates.append({"error": "Risk not found or unauthorized", "risk_id": risk_id})
                    continue
                
                # Update risk
                success = await risk_repo.update_finalized_risk_additional_data(risk_id, update_data)
                if success:
                    updated_count += 1
                else:
                    failed_updates.append({"error": "Update failed", "risk_id": risk_id})
                    
            except Exception as e:
                failed_updates.append({"error": str(e), "risk_id": update_data.get("risk_id")})
        
        return BulkRiskUpdateResponse(
            success=True,
            message=f"Updated {updated_count} risks successfully",
            updated_count=updated_count,
            failed_updates=failed_updates
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk update error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk update"
        )