from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.connection import connect_to_mongo, close_mongo_connection

def create_app() -> FastAPI:
    app = FastAPI(
        title="Risk Assessment Chatbot API",
        description="AI-driven conversational Risk Assessment Chatbot for ISO 27001",
        version="1.0.0"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on your frontend domain
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event():
        await connect_to_mongo()

    @app.on_event("shutdown")
    async def shutdown_event():
        await close_mongo_connection()

    return app
