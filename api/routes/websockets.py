from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.websockets import WebSocketState
from typing import Dict, List, Any, Optional
import json
import asyncio
from datetime import datetime
from langchain_core.messages import HumanMessage

from api.schemas import WebSocketMessage, WebSocketResponse
from api.auth import auth_manager, session_manager, validate_session_access
from graph import stream_risk_workflow, get_workflow_state, update_workflow_state, initialize_user_session
from config import get_logger

logger = get_logger(__name__)

class ConnectionManager:
    """Manage WebSocket connections for real-time communication"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, str] = {}  # user_id -> connection_id
        
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str):
        """Accept WebSocket connection and register user"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.user_connections[user_id] = connection_id
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "data": {
                "connection_id": connection_id,
                "message": "WebSocket connection established",
                "timestamp": datetime.utcnow().isoformat()
            }
        }, websocket)
    
    def disconnect(self, connection_id: str, user_id: Optional[str] = None):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
    
    async def send_user_message(self, message: dict, user_id: str):
        """Send message to specific user"""
        connection_id = self.user_connections.get(user_id)
        if connection_id and connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await self.send_personal_message(message, websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for websocket in self.active_connections.values():
            await self.send_personal_message(message, websocket)
    
    def get_user_connection(self, user_id: str) -> Optional[WebSocket]:
        """Get WebSocket for specific user"""
        connection_id = self.user_connections.get(user_id)
        if connection_id:
            return self.active_connections.get(connection_id)
        return None

# Global connection manager
manager = ConnectionManager()

router = APIRouter(prefix="/api/ws", tags=["websocket"])

@router.websocket("/chat/{user_id}")
async def websocket_chat_endpoint(websocket: WebSocket, user_id: str, token: Optional[str] = None):
    """
    WebSocket endpoint for real-time chat communication
    """
    
    connection_id = f"ws_{user_id}_{datetime.utcnow().timestamp()}"
    
    try:
        # Authenticate user
        if token:
            try:
                token_data = auth_manager.verify_token(token)
                if token_data.get("user_id") != user_id:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
                    return
            except Exception:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return
        
        # Connect WebSocket
        await manager.connect(websocket, connection_id, user_id)
        
        # Update session activity
        session_manager.update_activity(user_id)
        
        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Validate message structure
                if not isinstance(message_data, dict) or "type" not in message_data:
                    await manager.send_personal_message({
                        "type": "error",
                        "data": {"error": "Invalid message format"}
                    }, websocket)
                    continue
                
                # Process different message types
                await handle_websocket_message(websocket, user_id, message_data)
                
                # Update user activity
                session_manager.update_activity(user_id)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected normally: {connection_id}")
                break
                
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "data": {"error": "Invalid JSON format"}
                }, websocket)
                
            except Exception as e:
                logger.error(f"WebSocket message processing error: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "data": {"error": "Message processing failed"}
                }, websocket)
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    
    finally:
        manager.disconnect(connection_id, user_id)

async def handle_websocket_message(websocket: WebSocket, user_id: str, message_data: dict):
    """Handle different types of WebSocket messages"""
    
    message_type = message_data.get("type")
    data = message_data.get("data", {})
    
    if message_type == "ping":
        # Handle ping/pong for connection keepalive
        await manager.send_personal_message({
            "type": "pong",
            "data": {"timestamp": datetime.utcnow().isoformat()}
        }, websocket)
        
    elif message_type == "chat":
        # Handle chat messages with streaming response
        await handle_chat_message(websocket, user_id, data)
        
    elif message_type == "popup_interaction":
        # Handle popup interactions
        await handle_popup_interaction(websocket, user_id, data)
        
    elif message_type == "status_request":
        # Handle status requests
        await handle_status_request(websocket, user_id, data)
        
    else:
        await manager.send_personal_message({
            "type": "error",
            "data": {"error": f"Unknown message type: {message_type}"}
        }, websocket)

async def handle_chat_message(websocket: WebSocket, user_id: str, data: dict):
    """Handle chat messages with real-time streaming"""
    
    try:
        message = data.get("message", "")
        thread_id = data.get("thread_id")
        
        if not message:
            await manager.send_personal_message({
                "type": "error",
                "data": {"error": "Message content is required"}
            }, websocket)
            return
        
        # Get or create thread ID
        if not thread_id:
            session = session_manager.get_session(user_id)
            if session:
                thread_id = session["thread_id"]
            else:
                # Initialize new session
                session_data = await initialize_user_session(user_id)
                thread_id = session_data["thread_id"]
        
        # Validate thread access
        if not await validate_session_access(user_id, thread_id):
            await manager.send_personal_message({
                "type": "error", 
                "data": {"error": "Invalid thread access"}
            }, websocket)
            return
        
        # Get current state
        current_state = await get_workflow_state(thread_id)
        if not current_state:
            session_data = await initialize_user_session(user_id)
            current_state = session_data["state"]
            thread_id = session_data["thread_id"]
        
        # Add user message
        messages = current_state.get("messages", [])
        messages.append(HumanMessage(content=message))
        current_state["messages"] = messages
        
        # Send acknowledgment
        await manager.send_personal_message({
            "type": "chat_response",
            "data": {
                "status": "processing",
                "message": "Processing your message...",
                "partial": True
            }
        }, websocket)
        
        # Stream workflow execution
        response_chunks = []
        final_result = None
        
        logger.info(f"Starting workflow stream for user {user_id}")
        
        async for chunk in stream_risk_workflow(current_state, thread_id):
            logger.info(f"Received workflow chunk: {list(chunk.keys())}")
            
            # LangGraph returns chunks with node names as keys, check each node result
            for node_name, node_result in chunk.items():
                logger.info(f"Processing node '{node_name}' result")
                
                # Check if this node result contains messages
                if isinstance(node_result, dict) and "messages" in node_result:
                    messages = node_result["messages"]
                    logger.info(f"Node '{node_name}' has {len(messages)} messages")
                    
                    if messages:
                        last_msg = messages[-1]
                        logger.info(f"Last message type: {type(last_msg)}, has content: {hasattr(last_msg, 'content')}")
                        
                        if hasattr(last_msg, 'content'):
                            logger.info(f"Message content: {last_msg.content[:100]}...")
                            
                            if not isinstance(last_msg, HumanMessage):
                                response_chunks.append(last_msg.content)
                                
                                logger.info(f"Sending chat_response to frontend from node '{node_name}'")
                                await manager.send_personal_message({
                                    "type": "chat_response",
                                    "data": {
                                        "status": "streaming",
                                        "message": last_msg.content,
                                        "partial": False
                                    }
                                }, websocket)
                            else:
                                logger.info("Skipping HumanMessage")
                
                # Update other chunk-level data for backwards compatibility
                if node_name in chunk:
                    final_result = {**final_result} if final_result else {}
                    if isinstance(node_result, dict):
                        final_result.update(node_result)
            
            # Check for stage updates and popup data in any node result
            for node_name, node_result in chunk.items():
                if isinstance(node_result, dict):
                    # Send stage updates
                    if "current_stage" in node_result:
                        logger.info(f"Sending stage update from '{node_name}': {node_result['current_stage']}")
                        await manager.send_personal_message({
                            "type": "stage_update",
                            "data": {
                                "stage": node_result["current_stage"],
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }, websocket)
                    
                    # Send popup data
                    if node_result.get("popup_type"):
                        logger.info(f"Sending popup from '{node_name}': {node_result.get('popup_type')}")
                        await manager.send_personal_message({
                            "type": "popup",
                            "data": {
                                "popup_type": node_result["popup_type"],
                                "popup_data": node_result.get("pending_popup", {}),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }, websocket)
            
            final_result = chunk
        
        logger.info(f"Workflow streaming complete. Response chunks: {len(response_chunks)}")
        
        # If no response was sent during streaming, check if there's a final message
        if not response_chunks and final_result and "messages" in final_result:
            messages = final_result["messages"]
            logger.info(f"Checking final messages: {len(messages)}")
            
            # Find the last AI message
            for msg in reversed(messages):
                if hasattr(msg, 'content') and not isinstance(msg, HumanMessage):
                    logger.info(f"Found final AI message: {msg.content[:100]}...")
                    await manager.send_personal_message({
                        "type": "chat_response",
                        "data": {
                            "status": "complete",
                            "message": msg.content,
                            "partial": False
                        }
                    }, websocket)
                    break
        
        # Send completion message
        completion_data = {
            "status": "complete",
            "current_stage": final_result.get("current_stage") if final_result else None,
            "current_intent": final_result.get("current_intent") if final_result else None,
            "awaiting_input": final_result.get("awaiting_user_input", False) if final_result else False,
            "thread_id": thread_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Sending chat_complete: {completion_data}")
        await manager.send_personal_message({
            "type": "chat_complete",
            "data": completion_data
        }, websocket)
        
    except Exception as e:
        logger.error(f"WebSocket chat error for user {user_id}: {e}", exc_info=True)
        await manager.send_personal_message({
            "type": "error",
            "data": {"error": "Failed to process chat message"}
        }, websocket)

async def handle_popup_interaction(websocket: WebSocket, user_id: str, data: dict):
    """Handle popup interactions through WebSocket"""
    
    try:
        thread_id = data.get("thread_id")
        popup_type = data.get("popup_type")
        action = data.get("action")
        interaction_data = data.get("data", {})
        
        if not all([thread_id, popup_type, action]):
            await manager.send_personal_message({
                "type": "error",
                "data": {"error": "Missing required popup interaction data"}
            }, websocket)
            return
        
        # Validate thread access
        if not await validate_session_access(user_id, thread_id):
            await manager.send_personal_message({
                "type": "error",
                "data": {"error": "Invalid thread access"}
            }, websocket)
            return
        
        # Process popup interaction based on type
        if popup_type == "risk_selection" and action == "submit":
            # Handle risk selection
            selected_risk_ids = interaction_data.get("selected_risk_ids", [])
            edited_risks = interaction_data.get("edited_risks", [])
            
            await update_workflow_state(thread_id, {
                "temp_data": {
                    "selected_risk_ids": selected_risk_ids,
                    "edited_risks": edited_risks
                },
                "current_intent": "finalize_risks",
                "popup_type": None,
                "pending_popup": None
            })
            
            # Process through workflow
            current_state = await get_workflow_state(thread_id)
            current_state["messages"].append(HumanMessage(content="Finalize the selected risks"))
            
            result = await stream_risk_workflow(current_state, thread_id)
            
            # Stream the finalization process
            async for chunk in result:
                if "messages" in chunk:
                    messages = chunk["messages"]
                    if messages:
                        last_msg = messages[-1]
                        if hasattr(last_msg, 'content'):
                            await manager.send_personal_message({
                                "type": "popup_response",
                                "data": {
                                    "popup_type": popup_type,
                                    "action": action,
                                    "status": "processing",
                                    "message": last_msg.content
                                }
                            }, websocket)
        
        elif popup_type == "data_collection" and action == "submit":
            # Handle data collection
            risks_data = interaction_data.get("risks_data", [])
            
            await update_workflow_state(thread_id, {
                "temp_data": {
                    "additional_data": risks_data
                },
                "current_intent": "fill_additional_data",
                "popup_type": None,
                "pending_popup": None
            })
            
            current_state = await get_workflow_state(thread_id)
            result = await stream_risk_workflow(current_state, thread_id)
            
            # Stream the data collection process
            async for chunk in result:
                if "current_stage" in chunk:
                    await manager.send_personal_message({
                        "type": "popup_response",
                        "data": {
                            "popup_type": popup_type,
                            "action": action,
                            "status": "complete",
                            "current_stage": chunk["current_stage"]
                        }
                    }, websocket)
        
        elif action == "cancel":
            # Handle popup cancellation
            await update_workflow_state(thread_id, {
                "popup_type": None,
                "pending_popup": None
            })
            
            await manager.send_personal_message({
                "type": "popup_response",
                "data": {
                    "popup_type": popup_type,
                    "action": action,
                    "status": "cancelled"
                }
            }, websocket)
        
        else:
            await manager.send_personal_message({
                "type": "error",
                "data": {"error": f"Unknown popup interaction: {popup_type} - {action}"}
            }, websocket)
        
    except Exception as e:
        logger.error(f"WebSocket popup interaction error for user {user_id}: {e}", exc_info=True)
        await manager.send_personal_message({
            "type": "error",
            "data": {"error": "Failed to process popup interaction"}
        }, websocket)

async def handle_status_request(websocket: WebSocket, user_id: str, data: dict):
    """Handle status requests through WebSocket"""
    
    try:
        request_type = data.get("request_type", "session")
        
        if request_type == "session":
            # Get session status
            session = session_manager.get_session(user_id)
            
            session_status = {
                "user_id": user_id,
                "session_active": session.get("active", False) if session else False,
                "thread_id": session.get("thread_id") if session else None,
                "last_activity": session.get("last_activity").isoformat() if session and session.get("last_activity") else None
            }
            
            await manager.send_personal_message({
                "type": "status_response",
                "data": {
                    "request_type": request_type,
                    "status": session_status
                }
            }, websocket)
        
        elif request_type == "workflow":
            # Get workflow status
            session = session_manager.get_session(user_id)
            if session:
                thread_id = session["thread_id"]
                current_state = await get_workflow_state(thread_id)
                
                workflow_status = {
                    "current_stage": current_state.get("current_stage") if current_state else None,
                    "current_intent": current_state.get("current_intent") if current_state else None,
                    "has_popup": current_state.get("popup_type") is not None if current_state else False,
                    "awaiting_input": current_state.get("awaiting_user_input", False) if current_state else False
                }
                
                await manager.send_personal_message({
                    "type": "status_response",
                    "data": {
                        "request_type": request_type,
                        "status": workflow_status
                    }
                }, websocket)
            else:
                await manager.send_personal_message({
                    "type": "error",
                    "data": {"error": "No active session found"}
                }, websocket)
        
        else:
            await manager.send_personal_message({
                "type": "error",
                "data": {"error": f"Unknown status request type: {request_type}"}
            }, websocket)
        
    except Exception as e:
        logger.error(f"WebSocket status request error for user {user_id}: {e}", exc_info=True)
        await manager.send_personal_message({
            "type": "error",
            "data": {"error": "Failed to process status request"}
        }, websocket)

@router.websocket("/notifications/{user_id}")
async def websocket_notifications_endpoint(websocket: WebSocket, user_id: str, token: Optional[str] = None):
    """
    WebSocket endpoint for real-time notifications and system updates
    """
    
    connection_id = f"notifications_{user_id}_{datetime.utcnow().timestamp()}"
    
    try:
        # Authenticate user
        if token:
            try:
                token_data = auth_manager.verify_token(token)
                if token_data.get("user_id") != user_id:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
                    return
            except Exception:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return
        
        # Connect WebSocket
        await manager.connect(websocket, connection_id, user_id)
        
        # Send initial notifications
        await manager.send_personal_message({
            "type": "notification",
            "data": {
                "message": "Notifications connected",
                "category": "system",
                "timestamp": datetime.utcnow().isoformat()
            }
        }, websocket)
        
        # Keep connection alive and handle notifications
        while True:
            try:
                # Send periodic heartbeat
                await asyncio.sleep(30)
                await manager.send_personal_message({
                    "type": "heartbeat",
                    "data": {"timestamp": datetime.utcnow().isoformat()}
                }, websocket)
                
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket notifications error: {e}")
    
    finally:
        manager.disconnect(connection_id, user_id)

# Utility functions for external use
async def send_notification_to_user(user_id: str, notification: dict):
    """Send notification to specific user if connected"""
    websocket = manager.get_user_connection(user_id)
    if websocket:
        await manager.send_personal_message({
            "type": "notification",
            "data": notification
        }, websocket)

async def broadcast_system_notification(notification: dict):
    """Broadcast system notification to all connected users"""
    await manager.broadcast({
        "type": "system_notification",
        "data": notification
    })

# Export router and utilities
__all__ = [
    "router", 
    "manager", 
    "send_notification_to_user", 
    "broadcast_system_notification"
]