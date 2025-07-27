from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Any, List
import logging
import json
import asyncio
from datetime import datetime

from graph.workflow import execute_workflow
from models.session_model import ChatMessage, ChatResponse
from graph.state.graph_state import GraphState
from database.repository import session_repository

logger = logging.getLogger(__name__)

router = APIRouter()

# Removed metadata models - metadata is now handled via WebSocket workflow

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[username] = websocket
        logger.info(f"🔗 WebSocket: User {username} connected")

    def disconnect(self, username: str):
        if username in self.active_connections:
            del self.active_connections[username]
            logger.info(f"🔌 WebSocket: User {username} disconnected")

    async def send_personal_message(self, message: dict, username: str):
        if username in self.active_connections:
            try:
                await self.active_connections[username].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {username}: {e}")
                self.disconnect(username)

manager = ConnectionManager()

@router.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket, username)
    await manager.send_personal_message({
        "type": "welcome",
        "message": f"🚀 Welcome {username}! I'm your Risk Assessment AI assistant. I'm here to help you with ISO 27001 risk assessments. How can I assist you today?",
        "timestamp": datetime.now().isoformat()
    }, username)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            if message_data.get("type") == "chat":
                await handle_chat_message(message_data, username)
    except WebSocketDisconnect:
        manager.disconnect(username)
    except Exception as e:
        logger.error(f"WebSocket error for {username}: {e}")
        manager.disconnect(username)

async def handle_chat_message(message_data: dict, username: str):
    logger.info(f"💬 CHAT_HANDLER: Received message from user: {username}")
    logger.info(f"💬 CHAT_HANDLER: Message content: '{message_data.get('message', '')[:100]}...' (truncated)")
    try:
        user_message = message_data.get("message", "")

        await manager.send_personal_message({
            "type": "typing",
            "message": "AI is thinking..."
        }, username)

        # Create GraphState with user input
        state = GraphState(
            user_message=user_message,
            username=username,
            session_id="",  # Will be set by workflow
            current_node="auth",
            user_id=None  # Will be set by workflow
        )

        result: GraphState = await execute_workflow(state)

        logger.info(f"💬 CHAT_HANDLER: Workflow completed, preparing response")
        response_data = {
            "type": "response",
            "message": result.response,
            "timestamp": datetime.now().isoformat(),
            "workflow_status": {
                "current_step": result.current_node,
                "intent": result.intent,
                "needs_clarification": result.requires_input,
                "show_metadata_popup": result.show_metadata_popup,
                "metadata_completed": result.metadata_completed,
            }
        }
        if result.draft_risks and result.show_risks:
            response_data["risks"] = result.draft_risks
            response_data["workflow_status"]["total_risks"] = len(result.draft_risks)
        
        # Include report data if available
        if result.session_data and "report_content" in result.session_data:
            response_data["report"] = {
                "content": result.session_data["report_content"],
                "title": result.session_data.get("report_title", "Risk Assessment Report"),
                "generated_at": datetime.now().isoformat()
            }

        await manager.send_personal_message(response_data, username)
    except Exception as e:
        logger.error(f"Error handling chat message for {username}: {e}")
        await manager.send_personal_message({
            "type": "error",
            "message": f"I apologize, but I encountered an error processing your request. Please try again. {e}",
            "timestamp": datetime.now().isoformat()
        }, username)

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    try:
        # Create GraphState with user input
        state = GraphState(
            user_message=message.message,
            username=message.username,
            session_id="",  # Will be set by workflow
            current_node="auth",
            user_id=None  # Will be set by workflow
        )

        result: GraphState = await execute_workflow(state)

        return ChatResponse(
            response=result.response,
            session_id=result.session_id,
            current_node=result.current_node,
            intent=result.intent,
            data={"draft_risks": result.draft_risks, "selected_risk_ids": result.selected_risk_ids},
            requires_input=result.requires_input
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/session/{session_id}")
async def get_session_status(session_id: str):
    """Get session status - handled by workflow"""
    # This endpoint would need to be handled by a workflow node
    # For now, return basic status
    return {"message": "Session status queries should be handled by workflow"}

@router.delete("/session/{session_id}")
async def end_session(session_id: str):
    """End session - handled by workflow"""
    # This endpoint would need to be handled by a workflow node
    # For now, return basic response
    return {"message": "Session termination should be handled by workflow"}

# Metadata saving is now handled via WebSocket workflow - no separate POST endpoint needed
