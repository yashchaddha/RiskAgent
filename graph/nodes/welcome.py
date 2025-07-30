from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from graph.state.graph_state import RiskAgentState, update_intent, set_error, clear_error, update_session_context
from config import llm_config, get_logger
from prompts import prompt_manager, get_welcome_prompt_new_user, get_welcome_prompt_returning_user, get_intent_prompt
import json
import time

logger = get_logger(__name__)

async def welcome_node(state: RiskAgentState) -> Dict[str, Any]:
    """
    Generate contextual welcome message based on user status
    """
    
    user_id = state.get("user_id")
    temp_data = state.get("temp_data", {})
    user_data = temp_data.get("user_data", {})
    
    logger.info(f"Welcome node called for user: {user_id}")
    
    try:
        if not user_data:
            error_msg = "No user data available for welcome message"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        client = llm_config.get_client()
        
        # Determine if new or returning user
        is_new_user = temp_data.get("new_user", False)
        progress_summary = temp_data.get("progress_summary", {})
        
        if is_new_user:
            # New user welcome
            prompt_data = get_welcome_prompt_new_user(
                user_data["name"], 
                user_data["organization"], 
                user_data["industry"]
            )
            logger.info(f"Generating new user welcome for: {user_data['name']}")
        else:
            # Returning user welcome
            prompt_data = get_welcome_prompt_returning_user(
                user_data["name"],
                user_data["organization"], 
                user_data["current_stage"],
                progress_summary
            )
            logger.info(f"Generating returning user welcome for: {user_data['name']}, stage: {user_data['current_stage']}")
        
        # Call LLM for welcome message
        start_time = time.time()
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_data["system"]},
                {"role": "user", "content": prompt_data["user"]}
            ],
            **llm_config.get_general_qa_params()
        )
        
        response_time = (time.time() - start_time) * 1000
        welcome_message = response.choices[0].message.content
        
        # Log LLM call
        logger.info(f"Welcome message generated in {response_time:.2f}ms, tokens: {response.usage.total_tokens}")
        
        # Update session context
        context_update = f"Welcome completed for {user_data['name']}, stage: {user_data['current_stage']}"
        
        return {
            **clear_error(state),
            **update_session_context(state, context_update),
            "messages": state.get("messages", []) + [
                AIMessage(content=welcome_message)
            ],
            "last_action": "welcome_message_generated"
        }
        
    except Exception as e:
        error_msg = f"Welcome node error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            **set_error(state, error_msg),
            "messages": state.get("messages", []) + [
                AIMessage(content="Welcome! I'm your Risk Management Assistant. How can I help you today?")
            ]
        }

async def intent_classification_node(state: RiskAgentState) -> Dict[str, Any]:
    """
    Classify user intent from their message
    """
    
    user_id = state.get("user_id")
    messages = state.get("messages", [])
    current_stage = state.get("current_stage")
    session_context = state.get("session_context", "")
    
    logger.info(f"Intent classification for user: {user_id}, stage: {current_stage}")
    
    try:
        # Get last user message
        if not messages:
            error_msg = "No messages available for intent classification"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        # Find last human message
        last_human_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human_message = msg.content
                break
        
        if not last_human_message:
            error_msg = "No user message found for intent classification"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        logger.info(f"Classifying intent for message: '{last_human_message[:100]}...'")
        
        # Format conversation context
        conversation_context = prompt_manager.format_conversation_context(
            [{"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content} 
             for m in messages[-5:]]  # Last 5 messages
        )
        
        # Get intent classification prompt
        prompt_data = get_intent_prompt(last_human_message, current_stage, conversation_context)
        
        client = llm_config.get_client()
        
        # Call LLM for intent classification
        start_time = time.time()
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_data["system"]},
                {"role": "user", "content": prompt_data["user"]}
            ],
            **llm_config.get_intent_classification_params()
        )
        
        response_time = (time.time() - start_time) * 1000
        predicted_intent = response.choices[0].message.content.strip()
        
        # Validate intent
        is_valid = prompt_manager.validate_intent(last_human_message, predicted_intent)
        
        if not is_valid:
            logger.warning(f"Intent validation failed for: '{predicted_intent}' with message: '{last_human_message}', using general_question")
            predicted_intent = "general_question"
        
        logger.info(f"Intent classified as: {predicted_intent} in {response_time:.2f}ms")
        
        # Log LLM call for monitoring
        logger.info(f"Intent classification - tokens: {response.usage.total_tokens}, time: {response_time:.2f}ms")
        
        return {
            **clear_error(state),
            **update_intent(state, predicted_intent),
            "last_action": f"intent_classified_{predicted_intent}"
        }
        
    except Exception as e:
        error_msg = f"Intent classification error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # Fallback to general_question intent
        return {
            **update_intent(state, "general_question"),
            "last_action": "intent_classification_failed_fallback"
        }

async def conversation_handler_node(state: RiskAgentState) -> Dict[str, Any]:
    """
    Handle conversation flow and determine next action based on intent
    This node decides routing based on classified intent
    """
    
    user_id = state.get("user_id")
    current_intent = state.get("current_intent")
    current_stage = state.get("current_stage")
    
    logger.info(f"Conversation handler - user: {user_id}, intent: {current_intent}, stage: {current_stage}")
    
    try:
        # Validate intent and stage compatibility
        valid_intents = [
            "general_question", "change_matrix", "generate_risks", "view_risks", 
            "finalize_risks", "fill_additional_data", "generate_report", 
            "approve_report", "reject_report"
        ]
        
        if current_intent not in valid_intents:
            logger.warning(f"Invalid intent detected: {current_intent}, defaulting to general_question")
            current_intent = "general_question"
        
        # Stage-specific intent validation
        stage_intent_validation = {
            "welcome": ["general_question", "change_matrix", "generate_risks"],
            "risk_generation": ["general_question", "change_matrix", "generate_risks", "view_risks", "finalize_risks"],
            "risk_editing": ["general_question", "change_matrix", "generate_risks", "view_risks", "finalize_risks"],
            "data_collection": ["general_question", "fill_additional_data", "view_risks"],
            "awaiting_report_approval": ["general_question", "approve_report", "reject_report", "view_risks"],
            "report_ready": ["general_question", "view_risks", "generate_risks"]
        }
        
        allowed_intents = stage_intent_validation.get(current_stage, valid_intents)
        
        if current_intent not in allowed_intents:
            logger.warning(f"Intent {current_intent} not allowed in stage {current_stage}")
            # Don't change intent, let the specific node handle the stage mismatch
        
        # Update routing information in temp_data for conditional edges
        routing_info = {
            "next_node": current_intent,
            "routing_reason": f"intent_{current_intent}_in_stage_{current_stage}",
            "timestamp": time.time()
        }
        
        return {
            **clear_error(state),
            "temp_data": {
                **state.get("temp_data", {}),
                "routing_info": routing_info
            },
            "last_action": f"conversation_routed_to_{current_intent}"
        }
        
    except Exception as e:
        error_msg = f"Conversation handler error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # Fallback routing to general_question
        return {
            **update_intent(state, "general_question"),
            "temp_data": {
                **state.get("temp_data", {}),
                "routing_info": {
                    "next_node": "general_question",
                    "routing_reason": "error_fallback",
                    "timestamp": time.time()
                }
            },
            "last_action": "conversation_handler_error_fallback"
        }