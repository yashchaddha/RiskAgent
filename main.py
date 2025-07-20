# main.py
import asyncio
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from loguru import logger
import os
from config.settings import settings, validate_settings
from database.connection import db_manager
from api.app import create_app

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper()))

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Risk Assessment Chat...")
    
    try:
        validate_settings()
        logger.info("✓ Configuration validated")
        
        await db_manager.connect_async()
        db_manager.connect()
        logger.info("✓ Database connected")
        
        os.makedirs("/reports", exist_ok=True)
        logger.info("✓ Directories created")
        
        logger.info("🎉 Application startup complete!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield

    logger.info("🛑 Shutting down Risk Assessment Chat...")
    db_manager.close()
    logger.info("✓ Database connections closed")
    logger.info("👋 Application shutdown complete!")

def create_application() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = create_app(lifespan=lifespan)
    return app

# Create the app instance
app = create_application()

if __name__ == "__main__":
    logger.info(f"🌐 Starting server on {settings.HOST}:{settings.PORT}")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    logger.info(f"📊 Environment: {'Development' if settings.DEBUG else 'Production'}")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST ,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )