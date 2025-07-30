from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from graph.state.graph_state import RiskAgentState, update_stage, set_error, clear_error
from database.repository import repo_factory
from models.models import UserLogin, UserRegistration, UserStage
from config import get_logger, settings
from datetime import datetime

logger = get_logger(__name__)

async def authentication_node(state: RiskAgentState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    temp_data = state.get("temp_data", {})
    
    logger.info(f"Authentication node called for user: {user_id}")
    
    try:
        action = temp_data.get("action")
        credentials = temp_data.get("credentials")
        
        if not action or not credentials:
            error_msg = "Missing authentication action or credentials"
            logger.error(f"Authentication error: {error_msg}")
            return set_error(state, error_msg)
        
        user_repo = repo_factory.user_repository
        
        if action == "login":
            # Handle user login
            login_data = UserLogin(**credentials)
            logger.info(f"Attempting login for user: {login_data.name}")
            
            user = await user_repo.authenticate_user(login_data)
            
            if user:
                logger.info(f"Login successful for user: {user.user_id}")
                
                # Update state with authenticated user
                return {
                    **clear_error(state),
                    **update_stage(state, user.current_stage),
                    "user_id": user.user_id,
                    "temp_data": {"authenticated_user": user.dict()},
                    "messages": state.get("messages", []) + [
                        AIMessage(content=f"Welcome back, {user.name}! Login successful.")
                    ]
                }
            else:
                error_msg = "Invalid credentials"
                logger.warning(f"Login failed for user: {login_data.name}")
                return {
                    **set_error(state, error_msg),
                    "messages": state.get("messages", []) + [
                        AIMessage(content="Login failed. Please check your credentials.")
                    ]
                }
        
        elif action == "register":
            # Handle user registration
            registration_data = UserRegistration(**credentials)
            logger.info(f"Attempting registration for user: {registration_data.name}")
            
            try:
                user = await user_repo.create_user(registration_data)
                logger.info(f"Registration successful for user: {user.user_id}")
                
                # Log user creation
                logger.info(f"New user created: {user.user_id}, org: {user.organization}, industry: {user.industry}")
                
                return {
                    **clear_error(state),
                    **update_stage(state, UserStage.WELCOME),
                    "user_id": user.user_id,
                    "temp_data": {"authenticated_user": user.dict(), "new_user": True},
                    "messages": state.get("messages", []) + [
                        AIMessage(content=f"Welcome {user.name}! Registration successful. Let's start your risk assessment journey.")
                    ]
                }
                
            except ValueError as e:
                error_msg = str(e)
                logger.warning(f"Registration failed for {registration_data.name}: {error_msg}")
                return {
                    **set_error(state, error_msg),
                    "messages": state.get("messages", []) + [
                        AIMessage(content=f"Registration failed: {error_msg}")
                    ]
                }
        
        else:
            error_msg = f"Unknown authentication action: {action}"
            logger.error(f"Authentication error: {error_msg}")
            return set_error(state, error_msg)
    
    except Exception as e:
        error_msg = f"Authentication node error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            **set_error(state, error_msg),
            "messages": state.get("messages", []) + [
                AIMessage(content="An error occurred during authentication. Please try again.")
            ]
        }

async def session_initialization_node(state: RiskAgentState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    logger.info(f"Session initialization for user: {user_id}")
    
    try:
        if not user_id:
            error_msg = "No user_id in state for session initialization"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        # Get user data from database
        user_repo = repo_factory.user_repository
        risk_repo = repo_factory.risk_repository
        
        user = await user_repo.get_user_by_id(user_id)
        if not user:
            error_msg = f"User not found: {user_id}"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        # Get user's risk data for context
        finalized_risks_count = await risk_repo.get_finalized_risks_count(user_id)
        generated_risks = await risk_repo.get_generated_risks_by_user(user_id)
        
        # Create session context
        session_context = f"User: {user.name}, Org: {user.organization}, Industry: {user.industry}, Stage: {user.current_stage}, Risks: {finalized_risks_count} finalized, {len(generated_risks)} generated"
        
        logger.info(f"Session initialized - {session_context}")
        
        # Store progress summary for welcome message
        progress_summary = {
            "finalized_risks_count": finalized_risks_count,
            "generated_risks_count": len(generated_risks),
            "matrix_size": f"{len(user.likelihood_scale)}x{len(user.impact_scale)}",
            "likelihood_scale": user.likelihood_scale,
            "impact_scale": user.impact_scale
        }
        
        return {
            **clear_error(state),
            **update_stage(state, user.current_stage),
            "session_context": session_context,
            "temp_data": {
                "user_data": user.dict(),
                "progress_summary": progress_summary,
                "session_initialized": True
            },
            "last_activity": datetime.utcnow()
        }
        
    except Exception as e:
        error_msg = f"Session initialization error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return set_error(state, error_msg)

async def logout_node(state: RiskAgentState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    logger.info(f"Logout requested for user: {user_id}")
    
    try:
        # Clean up session state
        return {
            "user_id": "",
            "current_stage": UserStage.WELCOME,
            "current_intent": None,
            "pending_popup": None,
            "popup_type": None,
            "awaiting_user_input": False,
            "session_context": None,
            "last_action": "logout",
            "temp_data": None,
            "error_message": None,
            "retry_count": 0,
            "messages": state.get("messages", []) + [
                AIMessage(content="You have been logged out successfully. Thank you for using the Risk Management Agent!")
            ],
            "last_activity": datetime.utcnow()
        }
        
    except Exception as e:
        error_msg = f"Logout error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return set_error(state, error_msg)