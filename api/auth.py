from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database.repository import repo_factory
from models.models import User
from config import settings, get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()

class AuthManager:
    """Handles authentication and JWT token management"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def get_password_hash(self, password: str) -> str:
        """Hash password for storage"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        try:
            to_encode = data.copy()
            
            if expires_delta:
                expire = datetime.now(timezone.utc) + expires_delta
            else:
                expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

            to_encode.update({"exp": expire})
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            
            logger.info(f"Access token created for user: {data.get('user_id', 'unknown')}, expires at: {expire} (in {self.access_token_expire_minutes} minutes)")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"Token creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("user_id")
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            return payload
            
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user credentials"""
        try:
            user_repo = repo_factory.user_repository
            
            from models.models import UserLogin  # <-- Add this import
            # Get user by username
            user = await user_repo.authenticate_user(UserLogin(name=username, password=password))
            
            if not user:
                logger.warning(f"Authentication failed for user: {username}")
                return None
            
            # In production, verify hashed password
            # if not self.verify_password(password, user.password):
            #     return None
            
            logger.info(f"User authenticated successfully: {user.user_id}")
            return user
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def register_user(self, username: str, password: str, organization: str, industry: str) -> Optional[User]:
        """Register new user"""
        try:
            user_repo = repo_factory.user_repository
            
            # Hash password in production
            # hashed_password = self.get_password_hash(password)
            
            from models.models import UserRegistration  # <-- Add this import
            registration_data = {
                "name": username,
                "password": password,  # Use hashed_password in production
                "organization": organization,
                "industry": industry
            }
            
            # Convert dict to UserRegistration model
            user = await user_repo.create_user(UserRegistration(**registration_data))
            logger.info(f"User registered successfully: {user.user_id}")
            return user
            
        except ValueError as e:
            logger.warning(f"Registration failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Registration error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )

# Global auth manager instance
auth_manager = AuthManager()

# Dependency functions
async def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication credentials provided"
        )
    
    return auth_manager.verify_token(credentials.credentials)

async def get_current_user(token_data: Dict[str, Any] = Depends(get_current_user_token)) -> User:
    """Get current user from token data"""
    try:
        user_id = token_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_repo = repo_factory.user_repository
        user = await user_repo.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not validate user"
        )

async def get_optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        token_data = auth_manager.verify_token(credentials.credentials)
        user_id = token_data.get("user_id")
        
        if user_id:
            user_repo = repo_factory.user_repository
            return await user_repo.get_user_by_id(user_id)
        
    except Exception:
        pass  # Ignore authentication errors for optional auth
    
    return None

# Session Management
class SessionManager:
    """Manage user sessions and thread IDs"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, user_id: str, thread_id: str) -> Dict[str, Any]:
        """Create new user session"""
        session_data = {
            "user_id": user_id,
            "thread_id": thread_id,
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "active": True
        }
        
        self.active_sessions[user_id] = session_data
        logger.info(f"Session created for user: {user_id}, thread: {thread_id}")
        
        return session_data
    
    def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active session for user"""
        return self.active_sessions.get(user_id)
    
    def update_activity(self, user_id: str):
        """Update last activity timestamp"""
        if user_id in self.active_sessions:
            self.active_sessions[user_id]["last_activity"] = datetime.now(timezone.utc)
    
    def end_session(self, user_id: str):
        """End user session"""
        if user_id in self.active_sessions:
            self.active_sessions[user_id]["active"] = False
            logger.info(f"Session ended for user: {user_id}")
    
    def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """Clean up inactive sessions"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        inactive_users = []
        
        for user_id, session in self.active_sessions.items():
            if session["last_activity"] < cutoff_time:
                inactive_users.append(user_id)
        
        for user_id in inactive_users:
            del self.active_sessions[user_id]
            logger.info(f"Cleaned up inactive session for user: {user_id}")
        
        return len(inactive_users)

# Global session manager
session_manager = SessionManager()

# Authentication decorators and utilities
def require_auth(func):
    """Decorator to require authentication"""
    async def wrapper(*args, **kwargs):
        # This would be used with FastAPI dependencies
        return await func(*args, **kwargs)
    return wrapper

def check_user_permissions(user: User, required_stage: Optional[str] = None) -> bool:
    """Check if user has required permissions"""
    if not user:
        return False
    
    if required_stage and user.current_stage != required_stage:
        logger.warning(f"User {user.user_id} access denied for stage {required_stage}")
        return False
    
    return True

async def get_user_thread_id(user: User) -> str:
    """Get or create thread ID for user"""
    session = session_manager.get_session(user.user_id)
    
    if session and session.get("active"):
        # Update activity and return existing thread
        session_manager.update_activity(user.user_id)
        return session["thread_id"]
    
    # Create new session
    from graph.state.graph_state import get_thread_id_for_user
    thread_id = get_thread_id_for_user(user.user_id)
    session_manager.create_session(user.user_id, thread_id)
    
    return thread_id

# Error handling for authentication
class AuthenticationError(Exception):
    """Custom authentication error"""
    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class AuthorizationError(Exception):
    """Custom authorization error"""
    def __init__(self, message: str, status_code: int = status.HTTP_403_FORBIDDEN):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

# Utility functions
def create_user_token_data(user: User) -> Dict[str, Any]:
    """Create token data payload for user"""
    return {
        "user_id": user.user_id,
        "username": user.name,
        "organization": user.organization,
        "industry": user.industry,
        "current_stage": user.current_stage
    }

async def validate_session_access(user_id: str, thread_id: str) -> bool:
    """Validate that user has access to the thread/session"""
    session = session_manager.get_session(user_id)
    
    if not session:
        return False
    
    if session.get("thread_id") != thread_id:
        logger.warning(f"Thread ID mismatch for user {user_id}: expected {session.get('thread_id')}, got {thread_id}")
        return False
    
    return session.get("active", False)

# Export main components
__all__ = [
    "auth_manager",
    "session_manager",
    "get_current_user",
    "get_current_user_token",
    "get_optional_current_user",
    "get_user_thread_id",
    "check_user_permissions",
    "validate_session_access",
    "create_user_token_data",
    "AuthenticationError",
    "AuthorizationError"
]