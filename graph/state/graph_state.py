from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage
from models.models import UserStage
from datetime import datetime

class RiskAgentState(TypedDict):
    # User identification and session
    user_id: str
    thread_id: str  # LangGraph thread for session management
    
    # Current workflow state
    current_stage: UserStage
    current_intent: Optional[str]
    
    # LangGraph built-in message history
    messages: List[BaseMessage]  # Automatic conversation memory
    
    # Workflow control
    pending_popup: Optional[Dict[str, Any]]  # Frontend popup data
    popup_type: Optional[str]  # Type of popup to trigger
    awaiting_user_input: bool  # For HITL checkpoints
    
    # Context for LLM calls
    session_context: Optional[str]  # Brief context summary
    last_action: Optional[str]  # Track last completed action
    
    # Temporary data for current operation
    temp_data: Optional[Dict[str, Any]]  # Temporary storage for operations
    
    # Error handling
    error_message: Optional[str]
    retry_count: int  # Track retries for failed operations
    
    # Timestamps
    last_activity: datetime
    session_start: datetime

# State update helper functions
def update_stage(state: RiskAgentState, new_stage: UserStage) -> Dict[str, Any]:
    """Update user stage and log the transition"""
    return {
        "current_stage": new_stage,
        "last_activity": datetime.utcnow(),
        "last_action": f"stage_transition_to_{new_stage}"
    }

def update_intent(state: RiskAgentState, intent: str) -> Dict[str, Any]:
    """Update current user intent"""
    return {
        "current_intent": intent,
        "last_activity": datetime.utcnow()
    }

def set_popup(state: RiskAgentState, popup_type: str, popup_data: Dict[str, Any]) -> Dict[str, Any]:
    """Set popup data for frontend"""
    return {
        "popup_type": popup_type,
        "pending_popup": popup_data,
        "last_activity": datetime.utcnow()
    }

def clear_popup(state: RiskAgentState) -> Dict[str, Any]:
    """Clear popup data"""
    return {
        "popup_type": None,
        "pending_popup": None,
        "last_activity": datetime.utcnow()
    }

def set_awaiting_input(state: RiskAgentState, awaiting: bool = True) -> Dict[str, Any]:
    """Set HITL checkpoint status"""
    return {
        "awaiting_user_input": awaiting,
        "last_activity": datetime.utcnow()
    }

def update_temp_data(state: RiskAgentState, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update temporary data storage"""
    current_temp = state.get("temp_data", {})
    current_temp.update(data)
    return {
        "temp_data": current_temp,
        "last_activity": datetime.utcnow()
    }

def clear_temp_data(state: RiskAgentState) -> Dict[str, Any]:
    """Clear temporary data"""
    return {
        "temp_data": None,
        "last_activity": datetime.utcnow()
    }

def set_error(state: RiskAgentState, error_msg: str) -> Dict[str, Any]:
    """Set error state"""
    retry_count = state.get("retry_count", 0)
    return {
        "error_message": error_msg,
        "retry_count": retry_count + 1,
        "last_activity": datetime.utcnow()
    }

def clear_error(state: RiskAgentState) -> Dict[str, Any]:
    """Clear error state"""
    return {
        "error_message": None,
        "retry_count": 0,
        "last_activity": datetime.utcnow()
    }

def update_session_context(state: RiskAgentState, context: str) -> Dict[str, Any]:
    """Update session context for LLM calls"""
    return {
        "session_context": context,
        "last_activity": datetime.utcnow()
    }

# State validation and utilities
def validate_state(state: RiskAgentState) -> bool:
    """Validate state structure"""
    required_fields = ["user_id", "current_stage", "messages"]
    return all(field in state for field in required_fields)

def get_conversation_history(state: RiskAgentState, max_messages: int = 10) -> List[BaseMessage]:
    """Get recent conversation history"""
    messages = state.get("messages", [])
    return messages[-max_messages:] if messages else []

def create_initial_state(user_id: str, thread_id: str) -> RiskAgentState:
    """Create initial state for new session"""
    now = datetime.utcnow()
    return RiskAgentState(
        user_id=user_id,
        thread_id=thread_id,
        current_stage=UserStage.WELCOME,
        current_intent=None,
        messages=[],
        pending_popup=None,
        popup_type=None,
        awaiting_user_input=False,
        session_context=None,
        last_action=None,
        temp_data=None,
        error_message=None,
        retry_count=0,
        last_activity=now,
        session_start=now
    )

def get_state_summary(state: RiskAgentState) -> Dict[str, Any]:
    """Get summary of current state for logging"""
    return {
        "user_id": state.get("user_id"),
        "current_stage": state.get("current_stage"),
        "current_intent": state.get("current_intent"),
        "message_count": len(state.get("messages", [])),
        "has_popup": state.get("popup_type") is not None,
        "awaiting_input": state.get("awaiting_user_input", False),
        "has_error": state.get("error_message") is not None,
        "last_activity": state.get("last_activity"),
        "session_duration": (
            datetime.utcnow() - state.get("session_start", datetime.utcnow())
        ).total_seconds() if state.get("session_start") else 0
    }

# Thread ID generation for LangGraph
def generate_thread_id(user_id: str) -> str:
    """Generate thread ID for LangGraph session management"""
    return f"risk_agent_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

def get_thread_id_for_user(user_id: str, session_id: Optional[str] = None) -> str:
    """Get consistent thread ID for user session"""
    if session_id:
        return f"risk_agent_{user_id}_{session_id}"
    return f"risk_agent_{user_id}_main"