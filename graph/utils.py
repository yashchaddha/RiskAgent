from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from graph.state.graph_state import RiskAgentState, create_initial_state, get_thread_id_for_user
from database.repository import repo_factory
from models.models import UserStage
from config import get_logger
import json

logger = get_logger(__name__)

async def initialize_user_session(user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        logger.info(f"Initializing session for user: {user_id}")
        
        # Get user data from database
        user_repo = repo_factory.user_repository
        user = await user_repo.get_user_by_id(user_id)
        
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        # Generate thread ID for LangGraph
        thread_id = get_thread_id_for_user(user_id, session_id)
        
        # Create initial state
        initial_state = create_initial_state(user_id, thread_id)
        
        # Get user's progress data
        risk_repo = repo_factory.risk_repository
        finalized_risks_count = await risk_repo.get_finalized_risks_count(user_id)
        generated_risks = await risk_repo.get_generated_risks_by_user(user_id)
        
        # Build progress summary
        progress_summary = {
            "finalized_risks_count": finalized_risks_count,
            "generated_risks_count": len(generated_risks),
            "matrix_size": f"{len(user.likelihood_scale)}x{len(user.impact_scale)}",
            "likelihood_scale": user.likelihood_scale,
            "impact_scale": user.impact_scale
        }
        
        # Update state with user data
        session_state = {
            **initial_state,
            "current_stage": user.current_stage,
            "temp_data": {
                "user_data": user.dict(),
                "progress_summary": progress_summary,
                "session_initialized": True
            }
        }
        
        logger.info(f"Session initialized - Thread: {thread_id}, Stage: {user.current_stage}")
        
        return {
            "state": session_state,
            "thread_id": thread_id,
            "user": user,
            "progress_summary": progress_summary
        }
        
    except Exception as e:
        logger.error(f"Session initialization error: {e}", exc_info=True)
        raise

async def validate_user_action(user_id: str, action: str, current_stage: UserStage) -> bool:
    """
    Validate if user action is allowed in current stage
    """
    
    stage_permissions = {
        UserStage.WELCOME: [
            "general_question", "change_matrix", "generate_risks", "help"
        ],
        UserStage.RISK_GENERATION: [
            "general_question", "change_matrix", "generate_risks", 
            "view_risks", "finalize_risks", "help"
        ],
        UserStage.RISK_EDITING: [
            "general_question", "change_matrix", "generate_risks", 
            "view_risks", "finalize_risks", "help"
        ],
        UserStage.DATA_COLLECTION: [
            "general_question", "fill_additional_data", "view_risks", "help"
        ],
        UserStage.AWAITING_REPORT_APPROVAL: [
            "general_question", "approve_report", "reject_report", 
            "view_risks", "help"
        ],
        UserStage.REPORT_READY: [
            "general_question", "view_risks", "generate_risks", "help"
        ]
    }
    
    allowed_actions = stage_permissions.get(current_stage, [])
    is_allowed = action in allowed_actions
    
    if not is_allowed:
        logger.warning(f"Action '{action}' not allowed in stage '{current_stage}' for user {user_id}")
    
    return is_allowed

async def get_user_context(user_id: str) -> Dict[str, Any]:
    """
    Get comprehensive user context for LLM calls
    """
    
    try:
        # Get user data
        user_repo = repo_factory.user_repository
        user = await user_repo.get_user_by_id(user_id)
        
        if not user:
            return {}
        
        # Get risk data
        risk_repo = repo_factory.risk_repository
        finalized_risks = await risk_repo.get_finalized_risks_by_user(user_id)
        generated_risks = await risk_repo.get_generated_risks_by_user(user_id)
        
        # Get report data
        report_repo = repo_factory.report_repository
        latest_report = await report_repo.get_latest_report_by_user(user_id)
        
        context = {
            "user": {
                "name": user.name,
                "organization": user.organization,
                "industry": user.industry,
                "current_stage": user.current_stage,
                "likelihood_scale": user.likelihood_scale,
                "impact_scale": user.impact_scale,
                "matrix_size": f"{len(user.likelihood_scale)}x{len(user.impact_scale)}"
            },
            "risks": {
                "finalized_count": len(finalized_risks),
                "generated_count": len(generated_risks),
                "total_assessed": len(finalized_risks)
            },
            "reports": {
                "has_reports": latest_report is not None,
                "latest_report_date": latest_report.generated_at if latest_report else None
            },
            "session": {
                "last_activity": datetime.utcnow().isoformat()
            }
        }
        
        return context
        
    except Exception as e:
        logger.error(f"Error getting user context: {e}", exc_info=True)
        return {}

def format_state_for_logging(state: RiskAgentState) -> Dict[str, Any]:
    """
    Format state for logging (remove sensitive data)
    """
    
    log_state = {
        "user_id": state.get("user_id"),
        "current_stage": state.get("current_stage"),
        "current_intent": state.get("current_intent"),
        "message_count": len(state.get("messages", [])),
        "has_popup": state.get("popup_type") is not None,
        "awaiting_input": state.get("awaiting_user_input", False),
        "has_error": state.get("error_message") is not None,
        "retry_count": state.get("retry_count", 0),
        "last_action": state.get("last_action"),
        "session_duration": (
            datetime.utcnow() - state.get("session_start", datetime.utcnow())
        ).total_seconds() if state.get("session_start") else 0
    }
    
    return log_state

async def cleanup_old_sessions(max_age_hours: int = 24) -> int:
    """
    Clean up old session data (if using persistent storage)
    Returns number of sessions cleaned up
    """
    
    try:
        # This would be implemented if using persistent checkpointer
        # For now, MemorySaver handles cleanup automatically
        logger.info(f"Session cleanup called (max_age: {max_age_hours}h)")
        return 0
        
    except Exception as e:
        logger.error(f"Session cleanup error: {e}", exc_info=True)
        return 0

def validate_popup_data(popup_type: str, popup_data: Dict[str, Any]) -> bool:
    """
    Validate popup data structure
    """
    
    if popup_type == "risk_selection":
        required_fields = ["type", "risks", "total_generated"]
        if not all(field in popup_data for field in required_fields):
            return False
        
        # Validate risk structure
        for risk in popup_data.get("risks", []):
            risk_fields = ["risk_id", "description", "impact", "likelihood", 
                          "treatment_strategy", "treatment_measures"]
            if not all(field in risk for field in risk_fields):
                return False
    
    elif popup_type == "data_collection":
        required_fields = ["type", "risks"]
        if not all(field in popup_data for field in required_fields):
            return False
        
        # Validate data collection risk structure
        for risk in popup_data.get("risks", []):
            if "risk_id" not in risk or "description" not in risk:
                return False
    
    return True

async def log_user_action(user_id: str, action: str, details: Dict[str, Any] = None):
    """
    Log user actions for audit and analytics
    """
    
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details or {},
            "session_type": "risk_management_agent"
        }
        
        logger.info(f"User Action: {json.dumps(log_entry)}")
        
        # Could also save to database for analytics
        
    except Exception as e:
        logger.error(f"Error logging user action: {e}", exc_info=True)

async def get_workflow_metrics(user_id: str) -> Dict[str, Any]:
    """
    Get workflow completion metrics for user
    """
    
    try:
        user_repo = repo_factory.user_repository
        risk_repo = repo_factory.risk_repository
        report_repo = repo_factory.report_repository
        
        user = await user_repo.get_user_by_id(user_id)
        if not user:
            return {}
        
        finalized_count = await risk_repo.get_finalized_risks_count(user_id)
        generated_risks = await risk_repo.get_generated_risks_by_user(user_id)
        reports = await report_repo.get_reports_by_user(user_id)
        
        # Calculate completion percentage
        completion_steps = {
            "user_registered": True,
            "risks_generated": len(generated_risks) > 0,
            "risks_finalized": finalized_count > 0,
            "data_collected": user.current_stage in [UserStage.AWAITING_REPORT_APPROVAL, UserStage.REPORT_READY],
            "report_generated": len(reports) > 0
        }
        
        completed_steps = sum(completion_steps.values())
        completion_percentage = (completed_steps / len(completion_steps)) * 100
        
        metrics = {
            "user_id": user_id,
            "organization": user.organization,
            "industry": user.industry,
            "current_stage": user.current_stage,
            "completion_percentage": completion_percentage,
            "steps_completed": completed_steps,
            "total_steps": len(completion_steps),
            "step_details": completion_steps,
            "statistics": {
                "risks_generated": len(generated_risks),
                "risks_finalized": finalized_count,
                "reports_created": len(reports),
                "matrix_size": f"{len(user.likelihood_scale)}x{len(user.impact_scale)}"
            },
            "timestamps": {
                "user_created": user.created_at.isoformat() if user.created_at else None,
                "last_updated": user.updated_at.isoformat() if user.updated_at else None
            }
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting workflow metrics: {e}", exc_info=True)
        return {}

# Export utility functions
__all__ = [
    "initialize_user_session",
    "validate_user_action", 
    "get_user_context",
    "format_state_for_logging",
    "cleanup_old_sessions",
    "validate_popup_data",
    "log_user_action",
    "get_workflow_metrics"
]