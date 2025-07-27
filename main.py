from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from api.routes import chat, risks, reports
from config.settings import settings
from database.connection import connect_to_mongo, close_mongo_connection
import uvicorn
import os
import logging
import logging.config
import json
import sys
import time

# Load logging configuration from JSON file
if os.path.exists('logging.json'):
    with open('logging.json', 'r') as f:
        config = json.load(f)
    logging.config.dictConfig(config)
    logger = logging.getLogger(__name__)
    logger.info("📋 Loaded logging configuration from logging.json")
else:
    # Fallback logging configuration
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log', encoding='utf-8')
        ],
        force=True  # Override any existing logging configuration
    )
    logger = logging.getLogger(__name__)
    logger.info("📋 Using fallback logging configuration")

# Configure uvicorn loggers to show our application logs
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(logging.INFO)

# Ensure our application loggers are visible
app_logger = logging.getLogger("api")
app_logger.setLevel(logging.INFO)

graph_logger = logging.getLogger("graph")
graph_logger.setLevel(logging.INFO)

app = FastAPI(
    title="Risk Assessment Chatbot",
    description="AI-driven conversational Risk Assessment Chatbot for ISO 27001",
    version="1.0.0"
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"🌐 HTTP: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"🌐 HTTP: {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}s)")
    
    return response

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Database events
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    logger.info("🔗 Connecting to MongoDB...")
    await connect_to_mongo()
    logger.info("✅ MongoDB connection established")
    logger.info("🎯 Risk Assessment Agent is ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    logger.info("🔌 Closing MongoDB connection...")
    await close_mongo_connection()
    logger.info("👋 Risk Assessment Agent shutdown complete")

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(risks.router, prefix="/api/risks", tags=["risks"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main frontend application"""
    html_path = "frontend/index.html"
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        return None

if __name__ == "__main__":
    logger.info("🚀 Starting Risk Assessment Agent...")
    
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,  # Disable uvicorn's default log config to use ours
        log_level="info"
    )
