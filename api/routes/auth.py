from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from api.schemas import (
    UserRegistrationRequest, UserLoginRequest, AuthResponse,
    SessionStatusResponse, ErrorResponse
)
from api.auth import (
    auth_manager, session_manager, get_current_user, get_user_thread_id,
    create_user_token_data, AuthenticationError
)
from graph import initialize_user_session
from models.models import User
from config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/register", response_model=AuthResponse)
async def register_user(request: UserRegistrationRequest) -> AuthResponse:
    """
    Register a new user and initialize their session
    """
    
    logger.info(f"Registration attempt for user: {request.name}")
    
    try:
        # Register user
        user = await auth_manager.register_user(
            username=request.name,
            password=request.password,
            organization=request.organization,
            industry=request.industry
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
        
        # Initialize user session with graph workflow
        session_data = await initialize_user_session(user.user_id)
        thread_id = session_data["thread_id"]
        
        # Trigger welcome workflow for new registration
        from graph import invoke_risk_workflow
        welcome_state = {
            **session_data["state"],
            "action": "register"
        }
        await invoke_risk_workflow(welcome_state, thread_id)
        
        # Create session
        session_manager.create_session(user.user_id, thread_id)
        
        # Generate JWT token
        token_data = create_user_token_data(user)
        access_token = auth_manager.create_access_token(token_data)
        
        logger.info(f"User registered successfully: {user.user_id}")
        
        return AuthResponse(
            success=True,
            message=f"Welcome {user.name}! Registration successful.",
            user_id=user.user_id,
            thread_id=thread_id,
            user_data={
                "user_id": user.user_id,
                "name": user.name,
                "organization": user.organization,
                "industry": user.industry,
                "current_stage": user.current_stage,
                "matrix_size": f"{len(user.likelihood_scale)}x{len(user.impact_scale)}"
            },
            token=access_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error for {request.name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error"
        )

@router.post("/login", response_model=AuthResponse)
async def login_user(request: UserLoginRequest) -> AuthResponse:
    """
    Authenticate user and create session
    """
    
    logger.info(f"Login attempt for user: {request.name}")
    
    try:
        # Authenticate user
        user = await auth_manager.authenticate_user(request.name, request.password)
        
        if not user:
            logger.warning(f"Login failed for user: {request.name}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Get or create thread ID
        thread_id = await get_user_thread_id(user)
        
        # Initialize/restore session
        try:
            session_data = await initialize_user_session(user.user_id)
            thread_id = session_data["thread_id"]
            
            # Trigger welcome workflow for login
            from graph import invoke_risk_workflow
            welcome_state = {
                **session_data["state"],
                "action": "login"
            }
            await invoke_risk_workflow(welcome_state, thread_id)
            
        except Exception as e:
            logger.warning(f"Session initialization failed, using existing: {e}")
        
        # Generate JWT token
        token_data = create_user_token_data(user)
        access_token = auth_manager.create_access_token(token_data)
        
        logger.info(f"User logged in successfully: {user.user_id}")
        
        return AuthResponse(
            success=True,
            message=f"Welcome back, {user.name}!",
            user_id=user.user_id,
            thread_id=thread_id,
            user_data={
                "user_id": user.user_id,
                "name": user.name,
                "organization": user.organization,
                "industry": user.industry,
                "current_stage": user.current_stage,
                "matrix_size": f"{len(user.likelihood_scale)}x{len(user.impact_scale)}"
            },
            token=access_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {request.name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error"
        )

@router.post("/logout", response_model=AuthResponse)
async def logout_user(current_user: User = Depends(get_current_user)) -> AuthResponse:
    """
    Logout user and end session
    """
    
    logger.info(f"Logout request for user: {current_user.user_id}")
    
    try:
        # End session
        session_manager.end_session(current_user.user_id)
        
        logger.info(f"User logged out successfully: {current_user.user_id}")
        
        return AuthResponse(
            success=True,
            message="Logged out successfully",
            user_id=None,
            thread_id=None,
            user_data=None,
            token=None
        )
        
    except Exception as e:
        logger.error(f"Logout error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/session", response_model=SessionStatusResponse)
async def get_session_status(current_user: User = Depends(get_current_user)) -> SessionStatusResponse:
    """
    Get current session status and user progress
    """
    
    logger.info(f"Session status request for user: {current_user.user_id}")
    
    try:
        # Get session info
        session = session_manager.get_session(current_user.user_id)
        
        # Get user progress
        from graph.utils import get_workflow_metrics
        metrics = await get_workflow_metrics(current_user.user_id)
        
        progress_summary = {
            "completion_percentage": metrics.get("completion_percentage", 0),
            "steps_completed": metrics.get("steps_completed", 0),
            "total_steps": metrics.get("total_steps", 5),
            "statistics": metrics.get("statistics", {}),
            "current_matrix": f"{len(current_user.likelihood_scale)}x{len(current_user.impact_scale)}"
        }
        
        return SessionStatusResponse(
            user_id=current_user.user_id,
            current_stage=current_user.current_stage,
            progress_summary=progress_summary,
            session_active=session.get("active", False) if session else False,
            last_activity=session.get("last_activity") if session else current_user.updated_at
        )
        
    except Exception as e:
        logger.error(f"Session status error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve session status"
        )

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(current_user: User = Depends(get_current_user)) -> AuthResponse:
    """
    Refresh JWT token for authenticated user
    """
    
    logger.info(f"Token refresh request for user: {current_user.user_id}")
    
    try:
        # Generate new token
        token_data = create_user_token_data(current_user)
        access_token = auth_manager.create_access_token(token_data)
        
        # Get current thread ID
        thread_id = await get_user_thread_id(current_user)
        
        logger.info(f"Token refreshed successfully for user: {current_user.user_id}")
        
        return AuthResponse(
            success=True,
            message="Token refreshed successfully",
            user_id=current_user.user_id,
            thread_id=thread_id,
            user_data={
                "name": current_user.name,
                "organization": current_user.organization,
                "industry": current_user.industry,
                "current_stage": current_user.current_stage,
                "matrix_size": f"{len(current_user.likelihood_scale)}x{len(current_user.impact_scale)}"
            },
            token=access_token
        )
        
    except Exception as e:
        logger.error(f"Token refresh error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.get("/validate", response_model=AuthResponse)
async def validate_token(current_user: User = Depends(get_current_user)) -> AuthResponse:
    """
    Validate current JWT token and return user info
    """
    
    logger.info(f"Token validation request for user: {current_user.user_id}")
    
    try:
        # Get current thread ID
        thread_id = await get_user_thread_id(current_user)
        
        return AuthResponse(
            success=True,
            message="Token is valid",
            user_id=current_user.user_id,
            thread_id=thread_id,
            user_data={
                "name": current_user.name,
                "organization": current_user.organization,
                "industry": current_user.industry,
                "current_stage": current_user.current_stage,
                "matrix_size": f"{len(current_user.likelihood_scale)}x{len(current_user.impact_scale)}"
            },
            token=None  # Don't return new token for validation
        )
        
    except Exception as e:
        logger.error(f"Token validation error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token validation failed"
        )

@router.delete("/session/{user_id}")
async def admin_end_session(
    user_id: str,
    current_user: User = Depends(get_current_user)
) -> AuthResponse:
    """
    Admin endpoint to end user session (for testing/admin purposes)
    """
    
    # In production, add admin role check
    logger.info(f"Admin session termination request for user: {user_id}")
    
    try:
        session_manager.end_session(user_id)
        
        return AuthResponse(
            success=True,
            message=f"Session ended for user {user_id}",
            user_id=None,
            thread_id=None,
            user_data=None,
            token=None
        )
        
    except Exception as e:
        logger.error(f"Admin session termination error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session termination failed"
        )

# Note: Exception handlers should be registered on the main FastAPI app, not on routers
# Move this to your main.py file:
# @app.exception_handler(AuthenticationError)
# async def auth_exception_handler(request, exc: AuthenticationError):
#     """Handle authentication errors"""
#     return AuthResponse(
#         success=False,
#         message=exc.message,
#         user_id=None,
#         thread_id=None,
#         user_data=None,
#         token=None
#     )
