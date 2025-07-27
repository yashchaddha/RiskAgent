import logging
from graph.state.graph_state import GraphState
from graph.tools.llm_tools import answer_faq
from database.repository import session_repository

logger = logging.getLogger(__name__)

async def knowledge_engine_node(state: GraphState) -> GraphState:
    logger.info("KNOWLEDGE_ENGINE_NODE: Handling FAQ, greeting, or help")
    
    try:
        # Check if user has risks and this is a greeting/general question
        if state.draft_risks and len(state.draft_risks) > 0 and is_greeting_or_general(state.user_message):
            # Handle greeting with risks context
            response = await generate_greeting_with_context(state)
            state.show_risks = True  # Show risks to user
        else:
            # Handle regular FAQ/help
            response = await answer_faq(state.user_message)
            response += "\n\nWhat would you like to do next?"
        
        # Update state attributes
        state.response = response
        state.current_node = "complete"
        state.resume_node = "complete"
        state.requires_input = True
        state.error = ""  # Clear any previous errors
        
        # Save state
        await session_repository.update_graph_state(state)
        logger.info("State updated after knowledge engine response")
        
    except Exception as e:
        logger.error(f"Failed to process knowledge engine request: {str(e)}")
        state.error = f"Knowledge engine failed: {str(e)}"
        state.response = "I apologize, but I encountered an error. Please try again."
        state.current_node = "complete"
        state.requires_input = True
    
    return state

def is_greeting_or_general(message: str) -> bool:
    """Check if message is a greeting or general question"""
    message_lower = message.lower().strip()
    greeting_keywords = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings"]
    general_keywords = ["how are you", "what's up", "status", "progress", "what do we have", "show me"]
    
    return any(keyword in message_lower for keyword in greeting_keywords + general_keywords)

async def generate_greeting_with_context(state: GraphState) -> str:
    """Generate a contextual greeting that shows user's progress"""
    
    total_risks = len(state.draft_risks)
    approved_count = sum(1 for risk in state.draft_risks if risk.get("is_approved", False))
    pending_count = total_risks - approved_count
    
    # Determine workflow stage
    if pending_count == 0 and total_risks > 0:
        stage = "ready for metadata collection"
        next_action = "You can proceed to the next step or continue reviewing risks."
    elif approved_count > 0:
        stage = "in progress"
        next_action = f"You still have {pending_count} risk(s) pending approval."
    else:
        stage = "just generated"
        next_action = "You can start reviewing and approving them."
    
    greeting_response = f"""👋 Hello! Great to see you back.

📊 **Your Risk Assessment Progress:**
• Total Risks: {total_risks}
• Approved: {approved_count}
• Pending: {pending_count}
• Status: {stage}

{next_action}

**What you can do:**
• Review your risks (they're displayed below)
• Approve individual risks: "Approve risk R-001"
• Update risk details: "Change likelihood of risk 1 to high"
• Remove risks: "Remove risk 2"
• Generate more risks: "Generate additional risks"
• Proceed to next step: "These all look good, let's proceed"

What would you like to do?"""

    return greeting_response