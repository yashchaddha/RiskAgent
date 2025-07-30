from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn

# Import routers
from api.routes.auth import router as auth_router
from api.routes.chat import router as chat_router
from api.routes.risks import router as risks_router
from api.routes.reports import report_router, matrix_router, metrics_router
from api.routes.websockets import router as websocket_router
# from api.routes.utils import router as utils_router

# Import middleware and configuration
from api.middleware import configure_middleware, health_manager
from database.config import db_config
from config import settings, get_logger
import os

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Risk Management Agent API...")
    
    try:
        # Initialize database connection
        await db_config.connect()
        logger.info("Database connection established")
        
        # Initialize health manager
        health_manager.increment_request()
        logger.info("Health monitoring initialized")
        
        # Additional startup tasks could go here
        # - Initialize caches
        # - Load models
        # - Validate configurations
        
        logger.info("Risk Management Agent API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Risk Management Agent API...")
    
    try:
        # Close database connection
        await db_config.disconnect()
        logger.info("Database connection closed")
        
        # Cleanup tasks
        # - Close connections
        # - Save state
        # - Cleanup resources
        
        logger.info("Risk Management Agent API shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)

# Create FastAPI application
app = FastAPI(
    title="Risk Management Agent API",
    description="REST API for conversational risk management with LangGraph workflow",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure middleware (order matters!)
configure_middleware(app)

# Include API routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(risks_router)
app.include_router(report_router)
app.include_router(matrix_router)
app.include_router(metrics_router)
app.include_router(websocket_router)
# app.include_router(utils_router)

# Mount static files if frontend directory exists
if os.path.exists("frontend"):
    static_dir = os.path.join(os.path.dirname(__file__), "frontend")
    app.mount("/static", StaticFiles(directory=static_dir), name="static_files")
    logger.info("Static files mounted from frontend directory")

@app.get("/", response_class=HTMLResponse)
async def root():
    # Check if frontend directory and index.html exist
    index_path = os.path.join("frontend", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return HTMLResponse(content=f.read())

# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception in {request.method} {request.url.path}: {exc}", exc_info=True)
    
    return {
        "success": False,
        "error": "Internal server error",
        "message": "An unexpected error occurred. Please try again later.",
    }

# Custom startup event for additional initialization
@app.on_event("startup")
async def startup_event():

    logger.info("Executing additional startup tasks...")
    
    try:
        # Validate configuration
        required_settings = ["openai_api_key", "secret_key", "mongodb_url"]
        for setting in required_settings:
            if not getattr(settings, setting, None):
                logger.warning(f"Missing configuration: {setting}")
        
        # Test basic functionality
        if settings.debug:
            logger.info("Debug mode enabled - running basic tests")
            
            # Test database connection
            try:
                await db_config.client.admin.command('ping')
                logger.info("Database connection test: PASSED")
            except Exception as e:
                logger.error(f"Database connection test: FAILED - {e}")
            
            # Test LLM configuration
            try:
                from config import llm_config
                client = llm_config.get_client()
                logger.info("LLM configuration test: PASSED")
            except Exception as e:
                logger.error(f"LLM configuration test: FAILED - {e}")
        
        logger.info("Startup tasks completed successfully")
        
    except Exception as e:
        logger.error(f"Error in startup tasks: {e}", exc_info=True)

# Add custom metadata to OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title="Risk Management Agent API",
        version="1.0.0",
        description="A comprehensive REST API for conversational risk management powered by LangGraph workflow",
        routes=app.routes,
    )
    
    # Add custom info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }
    
    openapi_schema["info"]["contact"] = {
        "name": "Risk Management Agent Support",
        "email": "support@example.com"
    }
    
    openapi_schema["info"]["license"] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
    
    # Add server information
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.riskagent.com",
            "description": "Production server"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Development server configuration
if __name__ == "__main__":
    logger.info("Starting development server...")
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
        server_header=False,
        date_header=False
    )