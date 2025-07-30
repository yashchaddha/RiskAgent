from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from typing import Dict, Any, AsyncGenerator
import json
import asyncio

from api.schemas import (
    ChatMessageRequest, ChatMessageResponse, StreamChatResponse,
    PopupInteractionRequest, PopupInteractionResponse
)
from api.auth import get_current_user, get_user_thread_id, validate_session_access
from graph import (
    invoke_risk_workflow, stream_risk_workflow, 
    get_workflow_state, update_workflow_state
)
from models.models import User
from config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user)
) -> ChatMessageResponse:
    """
    Send a message to the Risk Management Agent
    """
    
    logger.info(f"Chat message from user {current_user.user_id}: '{request.message[:100]}...'")
    
    try:
        # Get or validate thread ID
        if request.thread_id:
            thread_id = request.thread_id
            # Validate access
            if not await validate_session_access(current_user.user_id, thread_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid thread access"
                )
        else:
            thread_id = await get_user_thread_id(current_user)
        
        # Get current workflow state
        current_state = await get_workflow_state(thread_id)
        
        if not current_state:
            # Initialize state if not exists
            from graph import initialize_user_session
            session_data = await initialize_user_session(current_user.user_id)
            current_state = session_data["state"]
            thread_id = session_data["thread_id"]
        
        # Add user message to state
        messages = current_state.get("messages", [])
        messages.append(HumanMessage(content=request.message))
        current_state["messages"] = messages
        
        # Invoke workflow
        result = await invoke_risk_workflow(current_state, thread_id)
        
        # Extract response data
        response_messages = result.get("messages", [])
        assistant_response = ""
        
        if response_messages:
            # Get last AI message
            for msg in reversed(response_messages):
                if hasattr(msg, 'content') and not isinstance(msg, HumanMessage):
                    assistant_response = msg.content
                    break
        
        # Check for popup data
        popup_data = result.get("pending_popup")
        popup_type = result.get("popup_type")
        
        # Get session data for frontend
        session_data = {
            "user_stage": result.get("current_stage"),
            "intent": result.get("current_intent"),
            "last_action": result.get("last_action"),
            "error": result.get("error_message")
        }
        
        logger.info(f"Chat response generated for user {current_user.user_id}")
        
        return ChatMessageResponse(
            success=True,
            message="Message processed successfully",
            response=assistant_response,
            current_stage=result.get("current_stage"),
            current_intent=result.get("current_intent"),
            popup_data=popup_data,
            popup_type=popup_type,
            awaiting_input=result.get("awaiting_user_input", False),
            session_data=session_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat message error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )

@router.post("/stream")
async def stream_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Stream response from the Risk Management Agent for real-time updates
    """
    
    logger.info(f"Stream chat message from user {current_user.user_id}: '{request.message[:100]}...'")
    
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            # Get or validate thread ID
            if request.thread_id:
                thread_id = request.thread_id
                if not await validate_session_access(current_user.user_id, thread_id):
                    yield f"data: {json.dumps({'type': 'error', 'data': {'error': 'Invalid thread access'}})}\n\n"
                    return
            else:
                thread_id = await get_user_thread_id(current_user)
            
            # Get current state
            current_state = await get_workflow_state(thread_id)
            
            if not current_state:
                from graph import initialize_user_session
                session_data = await initialize_user_session(current_user.user_id)
                current_state = session_data["state"]
                thread_id = session_data["thread_id"]
            
            # Add user message
            messages = current_state.get("messages", [])
            messages.append(HumanMessage(content=request.message))
            current_state["messages"] = messages
            
            # Send initial acknowledgment
            yield f"data: {json.dumps({'type': 'message', 'data': {'content': 'Processing your message...', 'partial': True}})}\n\n"
            
            # Stream workflow execution
            final_result = None
            async for chunk in stream_risk_workflow(current_state, thread_id):
                if "messages" in chunk:
                    messages = chunk["messages"]
                    if messages:
                        last_msg = messages[-1]
                        if hasattr(last_msg, 'content') and not isinstance(last_msg, HumanMessage):
                            yield f"data: {json.dumps({'type': 'message', 'data': {'content': last_msg.content, 'partial': False}})}\n\n"
                
                # Update with any stage changes
                if "current_stage" in chunk:
                    yield f"data: {json.dumps({'type': 'stage_update', 'data': {'stage': chunk['current_stage']}})}\n\n"
                
                # Handle popup data
                if chunk.get("popup_type"):
                    popup_data = {
                        "popup_type": chunk["popup_type"],
                        "popup_data": chunk.get("pending_popup", {})
                    }
                    yield f"data: {json.dumps({'type': 'popup', 'data': popup_data})}\n\n"
                
                final_result = chunk
            
            # Send completion
            completion_data = {
                "current_stage": final_result.get("current_stage") if final_result else None,
                "current_intent": final_result.get("current_intent") if final_result else None,
                "awaiting_input": final_result.get("awaiting_user_input", False) if final_result else False
            }
            yield f"data: {json.dumps({'type': 'complete', 'data': completion_data})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error for user {current_user.user_id}: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': 'Stream processing failed'}})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.post("/popup/interact", response_model=PopupInteractionResponse)
async def handle_popup_interaction(
    request: PopupInteractionRequest,
    current_user: User = Depends(get_current_user)
) -> PopupInteractionResponse:
    """
    Handle user interactions with popups (risk selection, data collection, etc.)
    """
    
    logger.info(f"Popup interaction from user {current_user.user_id}: {request.popup_type} - {request.action}")
    
    try:
        # Validate thread access
        if not await validate_session_access(current_user.user_id, request.thread_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid thread access"
            )
        
        # Handle different popup types
        if request.popup_type == "risk_selection" and request.action == "submit":
            # Handle risk selection submission
            result = await _handle_risk_selection(request, current_user)
            
        elif request.popup_type == "data_collection" and request.action == "submit":
            # Handle data collection submission
            result = await _handle_data_collection(request, current_user)
            
        elif request.action == "cancel":
            # Handle popup cancellation
            result = await _handle_popup_cancel(request, current_user)
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown popup interaction: {request.popup_type} - {request.action}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Popup interaction error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process popup interaction"
        )

async def _handle_risk_selection(request: PopupInteractionRequest, user: User) -> PopupInteractionResponse:
    """Handle risk selection popup submission"""
    
    data = request.data
    selected_risk_ids = data.get("selected_risk_ids", [])
    edited_risks = data.get("edited_risks", [])
    
    if not selected_risk_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No risks selected"
        )
    
    # Update workflow state with selection
    await update_workflow_state(request.thread_id, {
        "temp_data": {
            "selected_risk_ids": selected_risk_ids,
            "edited_risks": edited_risks
        },
        "current_intent": "finalize_risks",
        "popup_type": None,
        "pending_popup": None
    })
    
    # Process finalization
    current_state = await get_workflow_state(request.thread_id)
    current_state["messages"].append(HumanMessage(content="Finalize the selected risks"))
    
    result = await invoke_risk_workflow(current_state, request.thread_id)
    
    logger.info(f"Risk selection processed: {len(selected_risk_ids)} risks selected")
    
    return PopupInteractionResponse(
        success=True,
        message=f"Successfully finalized {len(selected_risk_ids)} risks",
        current_stage=result.get("current_stage"),
        redirect_to_chat=True
    )

async def _handle_data_collection(request: PopupInteractionRequest, user: User) -> PopupInteractionResponse:
    """Handle data collection popup submission"""
    
    data = request.data
    risks_data = data.get("risks_data", [])
    
    if not risks_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No risk data provided"
        )
    
    # Update workflow state with additional data
    await update_workflow_state(request.thread_id, {
        "temp_data": {
            "additional_data": risks_data
        },
        "current_intent": "fill_additional_data",
        "popup_type": None,
        "pending_popup": None
    })
    
    # Process data collection
    current_state = await get_workflow_state(request.thread_id)
    result = await invoke_risk_workflow(current_state, request.thread_id)
    
    logger.info(f"Data collection processed: {len(risks_data)} risks updated")
    
    return PopupInteractionResponse(
        success=True,
        message=f"Successfully updated {len(risks_data)} risks with additional data",
        current_stage=result.get("current_stage"),
        redirect_to_chat=True
    )

async def _handle_popup_cancel(request: PopupInteractionRequest, user: User) -> PopupInteractionResponse:
    """Handle popup cancellation"""
    
    # Clear popup state
    await update_workflow_state(request.thread_id, {
        "popup_type": None,
        "pending_popup": None
    })
    
    logger.info(f"Popup cancelled: {request.popup_type}")
    
    return PopupInteractionResponse(
        success=True,
        message="Popup cancelled",
        redirect_to_chat=True
    )

@router.get("/history/{thread_id}")
async def get_chat_history(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    limit: int = 50
):
    """
    Get chat history for a thread
    """
    
    logger.info(f"Chat history request from user {current_user.user_id} for thread {thread_id}")
    
    try:
        # Validate thread access
        if not await validate_session_access(current_user.user_id, thread_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid thread access"
            )
        
        # Get workflow state
        current_state = await get_workflow_state(thread_id)
        
        if not current_state:
            return {"success": True, "messages": [], "total_count": 0}
        
        # Extract messages
        messages = current_state.get("messages", [])
        
        # Format messages for frontend
        formatted_messages = []
        for msg in messages[-limit:]:
            if hasattr(msg, 'content'):
                formatted_messages.append({
                    "content": msg.content,
                    "role": "user" if isinstance(msg, HumanMessage) else "assistant",
                    "timestamp": getattr(msg, 'timestamp', None)
                })
        
        return {
            "success": True,
            "messages": formatted_messages,
            "total_count": len(messages),
            "current_stage": current_state.get("current_stage"),
            "current_intent": current_state.get("current_intent")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat history error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )

@router.delete("/clear/{thread_id}")
async def clear_chat_history(
    thread_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Clear chat history for a thread (keep user data and progress)
    """
    
    logger.info(f"Chat clear request from user {current_user.user_id} for thread {thread_id}")
    
    try:
        # Validate thread access
        if not await validate_session_access(current_user.user_id, thread_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid thread access"
            )
        
        # Clear only messages, keep workflow state
        await update_workflow_state(thread_id, {
            "messages": [],
            "current_intent": None,
            "popup_type": None,
            "pending_popup": None,
            "error_message": None
        })
        
        return {
            "success": True,
            "message": "Chat history cleared successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat clear error for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear chat history"
        )