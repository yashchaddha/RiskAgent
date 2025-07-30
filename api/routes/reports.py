from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from langchain_core.messages import HumanMessage
from typing import Optional, List
import tempfile
import os

from api.schemas import (
    ReportApprovalRequest, ReportApprovalResponse, ReportViewResponse,
    MatrixUpdateRequest, MatrixUpdateResponse, WorkflowMetricsResponse,
    ExportRequest, ExportResponse
)
from api.auth import get_current_user, validate_session_access
from graph import invoke_risk_workflow, get_workflow_state, update_workflow_state
from database.repository import repo_factory
from models.models import User
from config import get_logger, get_matrix_scales, MATRIX_CONFIGS

logger = get_logger(__name__)

# Report endpoints
report_router = APIRouter(prefix="/api/reports", tags=["reports"])

@report_router.post("/approve", response_model=ReportApprovalResponse)
async def approve_report_generation(
    request: ReportApprovalRequest,
    current_user: User = Depends(get_current_user)
) -> ReportApprovalResponse:
    """
    Handle HITL approval for report generation
    """
    
    logger.info(f"Report approval request from user {current_user.user_id}: approved={request.approved}")
    
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
        
        # Set appropriate intent based on approval
        if request.approved:
            intent_message = "Yes, generate my risk report"
            current_intent = "approve_report"
        else:
            intent_message = "No, let me review my risks first"
            current_intent = "reject_report"
        
        # Add user response and set intent
        messages = current_state.get("messages", [])
        messages.append(HumanMessage(content=intent_message))
        
        current_state["messages"] = messages
        current_state["current_intent"] = current_intent
        
        # Process through workflow
        result = await invoke_risk_workflow(current_state, request.thread_id)
        
        # Extract response
        response_messages = result.get("messages", [])
        assistant_response = ""
        if response_messages:
            last_msg = response_messages[-1]
            if hasattr(last_msg, 'content'):
                assistant_response = last_msg.content
        
        # Check if report was generated
        temp_data = result.get("temp_data", {})
        report_id = temp_data.get("report_id")
        
        if request.approved and report_id:
            message = "Report generation approved and completed successfully"
        elif request.approved:
            message = "Report generation approved and in progress"
        else:
            message = "Report generation postponed - you can review your risks"
        
        logger.info(f"Report approval processed for user {current_user.user_id}")
        
        return ReportApprovalResponse(
            success=True,
            message=message,
            current_stage=result.get("current_stage"),
            report_id=report_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report approval error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process report approval"
        )

@report_router.get("/view", response_model=ReportViewResponse)
async def view_reports(
    current_user: User = Depends(get_current_user),
    report_id: Optional[str] = Query(None),
    latest: bool = Query(False)
) -> ReportViewResponse:
    """
    View user's risk reports
    """
    
    logger.info(f"Report view request from user {current_user.user_id}")
    
    try:
        report_repo = repo_factory.report_repository
        
        if report_id:
            # Get specific report
            report = await report_repo.get_report_by_id(report_id)
            
            if not report or report.user_id != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Report not found"
                )
            
            formatted_report = {
                "report_id": report.report_id,
                "organization": report.organization,
                "industry": report.industry,
                "total_risks": report.total_risks,
                "high_priority_risks": report.high_priority_risks,
                "report_content": report.report_content,
                "generated_at": report.generated_at.isoformat()
            }
            
            return ReportViewResponse(
                success=True,
                report=formatted_report
            )
        
        elif latest:
            # Get latest report
            report = await report_repo.get_latest_report_by_user(current_user.user_id)
            
            if not report:
                return ReportViewResponse(
                    success=True,
                    report=None
                )
            
            formatted_report = {
                "report_id": report.report_id,
                "organization": report.organization,
                "industry": report.industry,
                "total_risks": report.total_risks,
                "high_priority_risks": report.high_priority_risks,
                "report_content": report.report_content,
                "generated_at": report.generated_at.isoformat()
            }
            
            return ReportViewResponse(
                success=True,
                report=formatted_report
            )
        
        else:
            # Get all reports for user
            reports = await report_repo.get_reports_by_user(current_user.user_id)
            
            formatted_reports = [
                {
                    "report_id": report.report_id,
                    "organization": report.organization,
                    "industry": report.industry,
                    "total_risks": report.total_risks,
                    "high_priority_risks": report.high_priority_risks,
                    "generated_at": report.generated_at.isoformat()
                }
                for report in reports
            ]
            
            return ReportViewResponse(
                success=True,
                reports_list=formatted_reports
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report view error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reports"
        )

@report_router.post("/export", response_model=ExportResponse)
async def export_report(
    request: ExportRequest,
    current_user: User = Depends(get_current_user)
) -> ExportResponse:
    """
    Export reports and risk data in various formats
    """
    
    logger.info(f"Report export request from user {current_user.user_id}: format={request.format}")
    
    try:
        # This would be implemented with actual file generation
        # For now, return a placeholder response
        
        file_id = f"export_{current_user.user_id}_{request.format}"
        download_url = f"/api/reports/download/{file_id}"
        
        return ExportResponse(
            success=True,
            download_url=download_url,
            file_id=file_id,
            expires_at=None  # Set expiration time in production
        )
        
    except Exception as e:
        logger.error(f"Report export error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export report"
        )

@report_router.get("/download-pdf")
async def download_report_pdf(
    report_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Download a report as PDF
    """
    
    logger.info(f"PDF download request from user {current_user.user_id} for report {report_id}")
    
    try:
        report_repo = repo_factory.report_repository
        
        if report_id:
            # Get specific report
            report = await report_repo.get_report_by_id(report_id)
        else:
            # Get latest report
            report = await report_repo.get_latest_report_by_user(current_user.user_id)
        
        if not report or report.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Prepare user data for PDF generation
        user_data = {
            "organization": report.organization,
            "industry": report.industry,
            "assessment_date": report.generated_at.strftime("%B %Y"),
            "matrix_size": "3x3"  # Default, could be stored in report if needed
        }
        
        # Generate PDF
        from utils.pdf_generator import generate_risk_report_pdf
        pdf_path = generate_risk_report_pdf(report.report_content, user_data)
        
        # Create filename for download
        org_name = report.organization.replace(' ', '_').lower()
        timestamp = report.generated_at.strftime("%Y%m%d")
        filename = f"risk_report_{org_name}_{timestamp}.pdf"
        
        logger.info(f"PDF generated successfully for report {report.report_id}")
        
        # Return file response with cleanup
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type='application/pdf',
            background=None  # File will be cleaned up automatically
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF download error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report"
        )

# Matrix management endpoints
matrix_router = APIRouter(prefix="/api/matrix", tags=["matrix_management"])

@matrix_router.put("/update", response_model=MatrixUpdateResponse)
async def update_risk_matrix(
    request: MatrixUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> MatrixUpdateResponse:
    """
    Update user's risk matrix configuration
    """
    
    logger.info(f"Matrix update request from user {current_user.user_id}: {request.matrix_size}")
    
    try:
        # Validate thread access
        if not await validate_session_access(current_user.user_id, request.thread_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid thread access"
            )
        
        # Validate matrix size
        if request.matrix_size not in MATRIX_CONFIGS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid matrix size. Must be one of: {list(MATRIX_CONFIGS.keys())}"
            )
        
        # Get current workflow state
        current_state = await get_workflow_state(request.thread_id)
        
        if not current_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Prepare message for matrix update
        message_content = f"Change my matrix to {request.matrix_size}"
        
        # Add user message and set intent
        messages = current_state.get("messages", [])
        messages.append(HumanMessage(content=message_content))
        
        current_state["messages"] = messages
        current_state["current_intent"] = "change_matrix"
        
        # Process through workflow
        result = await invoke_risk_workflow(current_state, request.thread_id)
        
        # Get new scales
        new_scales = get_matrix_scales(request.matrix_size)
        
        logger.info(f"Matrix updated to {request.matrix_size} for user {current_user.user_id}")
        
        return MatrixUpdateResponse(
            success=True,
            message=f"Risk matrix updated to {request.matrix_size} successfully",
            new_likelihood_scale=new_scales["likelihood_scale"],
            new_impact_scale=new_scales["impact_scale"],
            matrix_size=request.matrix_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Matrix update error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update risk matrix"
        )

@matrix_router.get("/current")
async def get_current_matrix(current_user: User = Depends(get_current_user)):
    """
    Get user's current risk matrix configuration
    """
    
    logger.info(f"Current matrix request from user {current_user.user_id}")
    
    try:
        # Get user scales
        user_repo = repo_factory.user_repository
        scales = await user_repo.get_user_scales(current_user.user_id)
        
        if not scales:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User matrix configuration not found"
            )
        
        matrix_size = f"{len(scales['likelihood_scale'])}x{len(scales['impact_scale'])}"
        
        return {
            "success": True,
            "matrix_size": matrix_size,
            "likelihood_scale": scales["likelihood_scale"],
            "impact_scale": scales["impact_scale"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current matrix error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve matrix configuration"
        )

@matrix_router.get("/options")
async def get_matrix_options():
    """
    Get available risk matrix options
    """
    
    try:
        options = []
        for size, config in MATRIX_CONFIGS.items():
            options.append({
                "matrix_size": size,
                "likelihood_scale": config["likelihood_scale"],
                "impact_scale": config["impact_scale"],
                "description": f"{size} matrix with {len(config['likelihood_scale'])} levels"
            })
        
        return {
            "success": True,
            "options": options
        }
        
    except Exception as e:
        logger.error(f"Get matrix options error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve matrix options"
        )

# Metrics and analytics endpoints
metrics_router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@metrics_router.get("/workflow", response_model=WorkflowMetricsResponse)
async def get_workflow_metrics(
    current_user: User = Depends(get_current_user)
) -> WorkflowMetricsResponse:
    """
    Get workflow completion metrics for user
    """
    
    logger.info(f"Workflow metrics request from user {current_user.user_id}")
    
    try:
        from graph.utils import get_workflow_metrics
        metrics = await get_workflow_metrics(current_user.user_id)
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Metrics not found"
            )
        
        return WorkflowMetricsResponse(**metrics)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workflow metrics error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow metrics"
        )

@metrics_router.get("/dashboard")
async def get_dashboard_data(current_user: User = Depends(get_current_user)):
    """
    Get comprehensive dashboard data for user
    """
    
    logger.info(f"Dashboard data request from user {current_user.user_id}")
    
    try:
        # Get metrics
        from graph.utils import get_workflow_metrics
        metrics = await get_workflow_metrics(current_user.user_id)
        
        # Get recent activity
        risk_repo = repo_factory.risk_repository
        report_repo = repo_factory.report_repository
        
        finalized_risks = await risk_repo.get_finalized_risks_by_user(current_user.user_id)
        generated_risks = await risk_repo.get_generated_risks_by_user(current_user.user_id)
        reports = await report_repo.get_reports_by_user(current_user.user_id)
        
        # Calculate risk distribution
        risk_distribution = {"Low": 0, "Medium": 0, "High": 0}
        for risk in finalized_risks:
            # Simple risk priority calculation
            if risk.impact in ["High", "Very High"] and risk.likelihood in ["High", "Very High"]:
                risk_distribution["High"] += 1
            elif risk.impact in ["Low", "Very Low"] and risk.likelihood in ["Low", "Very Low"]:
                risk_distribution["Low"] += 1
            else:
                risk_distribution["Medium"] += 1
        
        dashboard_data = {
            "user": {
                "name": current_user.name,
                "organization": current_user.organization,
                "industry": current_user.industry,
                "current_stage": current_user.current_stage
            },
            "metrics": metrics,
            "risk_summary": {
                "total_generated": len(generated_risks),
                "total_finalized": len(finalized_risks),
                "total_reports": len(reports),
                "risk_distribution": risk_distribution
            },
            "recent_activity": {
                "last_risk_generated": generated_risks[0].created_at.isoformat() if generated_risks else None,
                "last_risk_finalized": max([r.created_at for r in finalized_risks]).isoformat() if finalized_risks else None,
                "last_report_generated": reports[0].generated_at.isoformat() if reports else None
            }
        }
        
        return {
            "success": True,
            "dashboard": dashboard_data
        }
        
    except Exception as e:
        logger.error(f"Dashboard data error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard data"
        )

# Export router instances
report_router = report_router
matrix_router = matrix_router  
metrics_router = metrics_router