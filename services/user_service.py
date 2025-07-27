from typing import Optional
from datetime import datetime
from bson import ObjectId
from models.user_model import UserModel
from graph.state.graph_state import GraphState
from database.repository import user_repository, session_repository
import logging

logger = logging.getLogger(__name__)

async def get_or_create_user(username: str, first_name: Optional[str] = None, 
                           last_name: Optional[str] = None, email: Optional[str] = None) -> UserModel:
    """Get existing user or create new one"""
    try:
        # Try to get existing user
        user = await user_repository.get_user_by_username(username)
        
        if user:
            # Update last login
            await user_repository.update_last_login(user.id)
            logger.info(f"User {username} logged in")
            return user
        else:
            # Create new user
            new_user = UserModel(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email
            )
            user = await user_repository.create_user(new_user)
            logger.info(f"New user {username} created")
            return user
            
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}")
        raise

async def get_or_create_graph_state(username: str) -> GraphState:
    """Get existing active graph state or create new one"""
    try:
        # Get or create user first
        user = await get_or_create_user(username)
        
        # Check for existing active graph state
        graph_state = await session_repository.get_active_graph_state_by_user(user.id)
        
        if graph_state:
            # Update activity
            graph_state.last_activity = datetime.utcnow()
            await session_repository.update_graph_state(graph_state)
            logger.info(f"Resuming graph state for user {username}")
            return graph_state
        else:
            # Create new graph state
            new_graph_state = GraphState(
                user_id=user.id,
                username=username,
                current_node="auth"
            )
            graph_state = await session_repository.create_graph_state(new_graph_state)
            logger.info(f"New graph state created for user {username}")
            return graph_state
            
    except Exception as e:
        logger.error(f"Error in get_or_create_graph_state: {e}")
        raise
