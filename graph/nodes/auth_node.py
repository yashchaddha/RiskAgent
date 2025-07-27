import logging
from graph.state.graph_state import GraphState
from services.user_service import get_or_create_user
from database.repository import session_repository

logger = logging.getLogger(__name__)

async def auth_node(state: GraphState) -> GraphState:
    """Authenticate user and load/create session."""
    # Try to load existing session for this user
    existing_state = await session_repository.get_graph_state_by_username(state.username)
    
    if existing_state:
        # Resume existing session, but update with new user message
        existing_state.user_message = state.user_message
        existing_state.requires_input = True
        existing_state.error = ""  # Clear any previous errors
        existing_state.response = ""
        
        # Always route to intent_parser - let it decide based on full context
        existing_state.current_node = "intent_parser"
        logger.info(f"Resuming session for user {state.username} -> intent_parser (will analyze context)")
        
        return existing_state
    
    # First-time authentication - create new session
    user = await get_or_create_user(state.username)
    
    # Update state with authentication info and initialize all fields
    state.user_id = user.id
    state.session_id = str(state.id)  # Use GraphState's own ID as session_id
    state.authenticated = True
    state.resume_node = "intent_parser"
    state.response = f"✅ Hello, {state.username}! How can I help you today?"
    state.current_node = "intent_parser"
    state.requires_input = True
    state.intent = ""  # Clear intent
    state.error = ""   # Clear errors
    state.is_active = True
    state.risks_approved = False
    state.approval_timestamp = None
    # Draft risks and other data will be initialized as empty lists/dicts by default
    
    # Save new session
    await session_repository.create_graph_state(state)
    logger.info(f"Created new session for user {state.username}")
    
    return state