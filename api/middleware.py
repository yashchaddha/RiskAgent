import time
import json
import traceback
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from api.schemas import ErrorResponse, ValidationErrorResponse
from api.auth import session_manager, AuthenticationError, AuthorizationError
from config import settings, get_logger
from graph.utils import log_user_action

logger = get_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive request/response logging"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing
        start_time = time.time()
        
        # Extract request info
        request_id = f"req_{int(start_time * 1000000)}"
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log request
        logger.info(f"Request {request_id}: {request.method} {request.url.path}")
        logger.debug(f"Request {request_id} details: IP={client_ip}, UA={user_agent[:100]}")
        
        # Add request ID to state
        request.state.request_id = request_id
        request.state.start_time = start_time
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(f"Response {request_id}: {response.status_code} in {process_time:.3f}s")
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"Request {request_id} failed after {process_time:.3f}s: {str(e)}")
            raise

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
            
        except AuthenticationError as e:
            logger.warning(f"Authentication error: {e.message}")
            return ORJSONResponse(
                status_code=e.status_code,
                content=ErrorResponse(
                    error=e.message,
                    error_code="AUTHENTICATION_FAILED"
                ).dict()
            )
        
        except AuthorizationError as e:
            logger.warning(f"Authorization error: {e.message}")
            return ORJSONResponse(
                status_code=e.status_code,
                content=ErrorResponse(
                    error=e.message,
                    error_code="AUTHORIZATION_FAILED"
                ).dict()
            )
        
        except ValidationError as e:
            logger.warning(f"Validation error: {e}")
            return ORJSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=ValidationErrorResponse(
                    validation_errors=[
                        {"field": err["loc"][-1], "message": err["msg"]}
                        for err in e.errors()
                    ]
                ).dict()
            )
        
        except HTTPException as e:
            logger.warning(f"HTTP exception: {e.detail}")
            return ORJSONResponse(
                status_code=e.status_code,
                content=ErrorResponse(
                    error=e.detail,
                    error_code="HTTP_EXCEPTION"
                ).dict()
            )
        
        except Exception as e:
            request_id = getattr(request.state, 'request_id', 'unknown')
            error_trace = traceback.format_exc()
            
            logger.error(f"Unhandled error in request {request_id}: {str(e)}")
            logger.error(f"Error traceback: {error_trace}")
            
            # Don't expose internal errors in production
            if settings.debug:
                error_details = {"traceback": error_trace}
            else:
                error_details = None
            
            return ORJSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=ErrorResponse(
                    error="Internal server error",
                    error_code="INTERNAL_ERROR",
                    details=error_details
                ).dict()
            )

class UserActivityMiddleware(BaseHTTPMiddleware):
    """Middleware to track user activity and update sessions"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract user info from token if available
        user_id = None
        
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                from api.auth import auth_manager
                token = auth_header.split(" ")[1]
                token_data = auth_manager.verify_token(token)
                user_id = token_data.get("user_id")
        except Exception:
            pass  # Ignore auth errors in middleware
        
        # Process request
        response = await call_next(request)
        
        # Update user activity if authenticated
        if user_id and response.status_code < 400:
            session_manager.update_activity(user_id)
            
            # Log user action for specific endpoints
            path = request.url.path
            method = request.method
            
            action_mapping = {
                ("POST", "/api/chat/message"): "chat_message",
                ("POST", "/api/risks/generate"): "risk_generation",
                ("POST", "/api/risks/finalize"): "risk_finalization",
                ("POST", "/api/reports/approve"): "report_approval",
                ("PUT", "/api/matrix/update"): "matrix_update"
            }
            
            action = action_mapping.get((method, path))
            if action:
                try:
                    await log_user_action(user_id, action, {
                        "endpoint": path,
                        "method": method,
                        "status_code": response.status_code
                    })
                except Exception as e:
                    logger.warning(f"Failed to log user action: {e}")
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""
    
    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.requests: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/health"]:
            return await call_next(request)
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        
        # Get user ID if authenticated
        user_id = None
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                from api.auth import auth_manager
                token = auth_header.split(" ")[1]
                token_data = auth_manager.verify_token(token)
                user_id = token_data.get("user_id")
        except Exception:
            pass
        
        # Use user_id or IP as identifier
        client_id = user_id or client_ip
        
        # Check rate limit
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        if client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > minute_ago
            ]
        else:
            self.requests[client_id] = []
        
        # Check if limit exceeded
        if len(self.requests[client_id]) >= self.calls_per_minute:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return ORJSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=ErrorResponse(
                    error="Rate limit exceeded",
                    error_code="RATE_LIMIT_EXCEEDED",
                    details={"limit": self.calls_per_minute, "window": "1 minute"}
                ).dict()
            )
        
        # Add current request
        self.requests[client_id].append(now)
        
        return await call_next(request)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Security headers and validation middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

# Exception handlers
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> ORJSONResponse:
    """Handle validation errors"""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    
    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ValidationErrorResponse(
            validation_errors=[
                {
                    "field": ".".join(str(loc) for loc in err["loc"]) if err["loc"] else "unknown",
                    "message": err["msg"],
                    "type": err["type"]
                }
                for err in exc.errors()
            ]
        ).dict()
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> ORJSONResponse:
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code} on {request.url.path}: {exc.detail}")
    
    return ORJSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).dict()
    )

async def general_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
    """Handle unexpected exceptions"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(f"Unhandled exception in request {request_id}: {str(exc)}")
    logger.error(f"Exception traceback: {traceback.format_exc()}")
    
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR"
        ).dict()
    )

# CORS configuration
def get_cors_middleware():
    """Get CORS middleware configuration"""
    return CORSMiddleware(
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization", 
            "X-Requested-With",
            "X-Request-ID"
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time"
        ]
    )

# Middleware configuration function
def configure_middleware(app):
    """Configure all middleware for the FastAPI app"""
    
    # Add CORS middleware first
    app.add_middleware(CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"]
    )
    
    # Add custom middleware in order
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RateLimitMiddleware, calls_per_minute=120)
    app.add_middleware(UserActivityMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(LoggingMiddleware)
    
    # Add exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("All middleware configured successfully")

# Utility functions for middleware
def get_client_info(request: Request) -> Dict[str, Any]:
    """Extract client information from request"""
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "referer": request.headers.get("referer"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "x_real_ip": request.headers.get("x-real-ip")
    }

def sanitize_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize request data for logging (remove sensitive info)"""
    sensitive_fields = ["password", "token", "secret", "key", "auth"]
    
    sanitized = {}
    for key, value in data.items():
        if any(field in key.lower() for field in sensitive_fields):
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    
    return sanitized

# Health check utilities
class HealthCheckManager:
    """Manage application health checks"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.request_count = 0
        self.error_count = 0
    
    def increment_request(self):
        """Increment request counter"""
        self.request_count += 1
    
    def increment_error(self):
        """Increment error counter"""
        self.error_count += 1
    
    async def check_database_health(self) -> bool:
        """Check database connectivity"""
        try:
            from database.config import db_config
            # Simple ping to check database
            await db_config.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def check_llm_health(self) -> bool:
        """Check LLM API availability"""
        try:
            from config import llm_config
            client = llm_config.get_client()
            
            # Simple test call
            response = await client.chat.completions.create(
                messages=[{"role": "user", "content": "test"}],
                model=llm_config.model,
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False
    
    def get_health_stats(self) -> Dict[str, Any]:
        """Get application health statistics"""
        uptime = datetime.utcnow() - self.start_time
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "requests_total": self.request_count,
            "errors_total": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "active_sessions": len(session_manager.active_sessions)
        }

# Global health check manager
health_manager = HealthCheckManager()

# Export main components
__all__ = [
    "configure_middleware",
    "LoggingMiddleware",
    "ErrorHandlingMiddleware",
    "UserActivityMiddleware",
    "RateLimitMiddleware",
    "SecurityMiddleware",
    "health_manager",
    "get_client_info",
    "sanitize_request_data"
]