import logging
import json
from typing import Dict, Any, List, Optional
from config.settings import settings
from graph.state.graph_state import GraphState
from database.repository import session_repository
from openai import AsyncOpenAI
import re

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key)

async def risk_reviewer_node(state: GraphState) -> GraphState:
    logger.info("RISK_REVIEWER_NODE: Processing user review action")
    
    try:
        # Clear any previous errors
        state.error = ""
        
        # Get current draft risks (direct field, not from session_data)
        draft_risks = state.draft_risks or []
        
        if not draft_risks:
            state.response = "No risks available to review. Please generate risks first."
            state.current_node = "intent_parser"
            state.requires_input = True
            await session_repository.update_graph_state(state)
            return state
        
        # Parse user intent using LLM
        user_intent = await parse_user_intent_for_risks(state.user_message, draft_risks)
        
        # Handle different actions based on confidence level
        if user_intent["confidence"] < 0.6:
            # Check if it's a simple greeting first
            if is_greeting_message(state.user_message):
                await handle_greeting_with_risks(state, draft_risks)
            else:
                # Low confidence - ask for clarification
                await handle_clarification_request(state, user_intent, draft_risks)
            
        elif user_intent["action"] == "update_risk":
            # User wants to update specific risk fields
            await handle_risk_update(state, user_intent)
            
        elif user_intent["action"] == "remove_risk":
            # User wants to completely reject/remove a risk
            await handle_risk_removal(state, user_intent)
            
        elif user_intent["action"] == "approve_risk":
            # User wants to approve specific risk(s)
            await handle_risk_approval(state, user_intent)
            
        elif user_intent["action"] == "finalize_all":
            # User accepts all current risks and wants to proceed
            await handle_finalize_all_risks(state)
            
        elif user_intent["action"] == "complex_operation":
            # Reject complex operations user can't handle
            await handle_complex_operation_rejection(state, user_intent)
            
        else:
            # Default: show current risks and ask for action
            await show_current_risks_for_review(state, draft_risks)
        
        # Save state after processing
        await session_repository.update_graph_state(state)
        logger.info("State updated after risk review processing")
        
    except Exception as e:
        logger.error(f"Failed to process risk review: {str(e)}")
        state.error = f"Risk review failed: {str(e)}"
        state.response = "Sorry, I encountered an error processing your review. Please try again."
        state.current_node = "risk_reviewer"
        state.requires_input = True
        
        try:
            await session_repository.update_graph_state(state)
        except Exception as save_error:
            logger.error(f"Failed to save error state: {str(save_error)}")
    
    return state

async def parse_user_intent_for_risks(user_message: str, draft_risks: List[Dict]) -> Dict[str, Any]:
    """Use LLM to parse user intent for risk operations"""
    
    # Create risk summary for context
    risks_summary = "\n".join([
        f"Risk {i+1}: {risk.get('risk_description', '')} (ID: {risk.get('risk_id', f'risk_{i+1}')})"
        for i, risk in enumerate(draft_risks)
    ])
    
    prompt = f"""
    You are a risk management assistant. Parse the user's message to understand what action they want to take on their risks.

    Current risks:
    {risks_summary}

    User message: "{user_message}"

    Determine the user's intent and respond with a JSON object containing:
    {{
        "action": "update_risk" | "remove_risk" | "approve_risk" | "finalize_all" | "complex_operation" | "clarification_needed",
        "risk_identifier": "risk_id or description snippet or number",
        "field_to_update": "likelihood" | "impact" | "risk_description" | "mitigation_strategy" | null,
        "new_value": "the new value they want to set",
        "confidence": 0.0-1.0,
        "reasoning": "brief explanation of your interpretation"
    }}

    Action types and rules:
    - "update_risk": User wants to modify ONE specific field of ONE specific risk (high confidence required)
    - "remove_risk": User wants to completely remove/reject ONE specific risk  
    - "approve_risk": User wants to approve ONE or MORE specific risks (add is_approved=true)
    - "finalize_all": User is satisfied with ALL risks and wants to proceed to next step
    - "complex_operation": User wants to do multiple operations at once - REJECT these
    - "clarification_needed": Message is ambiguous, unclear, or too complex

    IMPORTANT RULES:
    1. Only allow SINGLE, SIMPLE operations per message
    2. If user wants to do multiple things at once → "complex_operation"
    3. Only high confidence (>0.6) for update_risk operations
    4. Be strict about field names - only allow: likelihood, impact, risk_description, mitigation_strategy

    Examples:
    - "Change the likelihood of risk 1 to high" → update_risk (confidence: 0.9)
    - "Remove the third risk" → remove_risk (confidence: 0.8)
    - "Approve risk 2" → approve_risk (confidence: 0.8)
    - "These all look good, let's proceed" → finalize_all (confidence: 0.9)
    - "Change risk 1 likelihood to high and remove risk 2" → complex_operation
    - "Update all risks to high likelihood" → complex_operation
    - "What's the weather?" → clarification_needed

    Respond only with valid JSON.
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a precise JSON parser for risk management operations. Be strict and conservative."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        result = json.loads(response.choices[0].message.content)
        logger.info(f"Parsed user intent: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to parse user intent: {e}")
        return {
            "action": "clarification_needed",
            "confidence": 0.0,
            "reasoning": f"Failed to parse intent: {str(e)}"
        }

async def handle_risk_update(state: GraphState, intent: Dict[str, Any]) -> None:
    """Handle updating specific fields of a risk"""
    
    # Find the risk to update
    risk_to_update, risk_index = find_risk_by_identifier(state.draft_risks, intent["risk_identifier"])
    
    if not risk_to_update:
        state.response = f"I couldn't find the risk you want to update: '{intent['risk_identifier']}'. Please be more specific or try again."
        state.current_node = "complete"
        state.requires_input = True
        return
    
    # Validate field name
    allowed_fields = ["likelihood", "impact", "risk_description", "mitigation_strategy"]
    field = intent["field_to_update"]
    
    if field not in allowed_fields:
        state.response = f"I can only update these fields: {', '.join(allowed_fields)}. Please specify one of these fields."
        state.current_node = "complete"
        state.requires_input = True
        return
    
    # Prepare update data for database manager
    update_data = {
        "operation": "update_risk",
        "risk_index": risk_index,
        "field": field,
        "new_value": intent["new_value"]
    }
    
    # Store update operation in session_data for database_manager to process
    state.session_data["pending_operation"] = update_data
    
    state.response = f"Updating the {field} of '{risk_to_update.get('risk_description', 'this risk')}' to '{intent['new_value']}'..."
    state.current_node = "database_manager"
    state.resume_node = "risk_reviewer"  # Come back here after DB operation
    state.requires_input = False

async def handle_risk_removal(state: GraphState, intent: Dict[str, Any]) -> None:
    """Handle completely removing a risk"""
    
    risk_to_remove, risk_index = find_risk_by_identifier(state.draft_risks, intent["risk_identifier"])
    
    if not risk_to_remove:
        state.response = f"I couldn't find the risk you want to remove: '{intent['risk_identifier']}'. Please be more specific."
        state.current_node = "complete"
        state.requires_input = True
        return
    
    # Prepare removal data for database manager
    removal_data = {
        "operation": "remove_risk",
        "risk_index": risk_index
    }
    
    state.session_data["pending_operation"] = removal_data
    
    state.response = f"Removing the risk: '{risk_to_remove.get('risk_description', 'this risk')}'..."
    state.current_node = "database_manager"
    state.resume_node = "risk_reviewer"
    state.requires_input = False

async def handle_risk_approval(state: GraphState, intent: Dict[str, Any]) -> None:
    """Handle approving specific risk(s) or all risks - adds is_approved=True"""
    
    risk_identifier = intent["risk_identifier"]
    
    # Handle "approve all" case
    if risk_identifier and risk_identifier.lower() in ["all", "everything", "all risks"]:
        # Approve all risks directly without going to database manager
        approved_count = 0
        for risk in state.draft_risks:
            if not risk.get("is_approved", False):
                risk["is_approved"] = True
                approved_count += 1
        
        if approved_count > 0:
            # Check if metadata already completed
            if not state.metadata_completed:
                state.response = f"✅ Approved all {approved_count} risks!\n\n🎉 All risks are now approved!\n\n📋 The metadata collection form will open automatically. Please provide additional details for each risk to complete your assessment."
                state.show_metadata_popup = True  # Automatically trigger metadata popup
            else:
                state.response = f"✅ Approved all {approved_count} risks!\n\n🎉 All risks are now approved!\n\n📊 Since metadata is already completed, proceeding to report generation..."
                state.current_node = "report_generator"
                state.resume_node = "report_generator"
                state.requires_input = False
            
            state.risks_approved = True
            state.show_risks = True  # Also show risks
            from datetime import datetime
            state.approval_timestamp = datetime.utcnow()
        else:
            # All already approved - check metadata status
            if not state.metadata_completed:
                state.response = "All risks are already approved! 🎉\n\n📋 The metadata collection form will open automatically. Please provide additional details for each risk to complete your assessment."
                state.show_metadata_popup = True  # Show popup if metadata not completed
            else:
                state.response = "All risks are already approved! 🎉\n\n📊 Since metadata is already completed, proceeding to report generation..."
                state.current_node = "report_generator"
                state.resume_node = "report_generator"
                state.requires_input = False
            state.show_risks = True
        
        state.current_node = "complete"
        state.show_risks = True
        state.requires_input = True
        return
    
    # Handle single risk approval
    risk_to_approve, risk_index = find_risk_by_identifier(state.draft_risks, risk_identifier)
    
    if not risk_to_approve:
        state.response = f"I couldn't find the risk you want to approve: '{risk_identifier}'. Please be more specific."
        state.current_node = "complete"
        state.requires_input = True
        return
    
    # Prepare approval data for database manager
    approval_data = {
        "operation": "approve_risk",
        "risk_index": risk_index
    }
    
    state.session_data["pending_operation"] = approval_data
    
    state.response = f"Approving the risk: '{risk_to_approve.get('risk_description', 'this risk')}'..."
    state.current_node = "database_manager"
    state.resume_node = "risk_reviewer"
    state.requires_input = False

async def handle_finalize_all_risks(state: GraphState) -> None:
    """Handle user accepting all current risks and moving to next step"""
    
    # Mark all risks as approved
    for risk in state.draft_risks:
        risk["is_approved"] = True
    
    state.response = "Great! All risks have been finalized. Moving to metadata collection..."
    state.current_node = "metadata_collector"
    state.resume_node = "metadata_collector"
    state.requires_input = False
    state.risks_approved = True
    
    from datetime import datetime
    state.approval_timestamp = datetime.utcnow()

async def handle_complex_operation_rejection(state: GraphState, intent: Dict[str, Any]) -> None:
    """Handle and reject complex operations that are too complicated"""
    
    state.response = f"""I can only handle one simple operation at a time. 

Your request seems to involve multiple operations: {intent.get('reasoning', 'multiple actions')}

Please break it down into single operations like:
• "Change the likelihood of risk 1 to high"
• "Remove risk 2"  
• "Approve risk 3"

What single operation would you like to do first?"""
    
    state.current_node = "complete"
    state.requires_input = True

async def handle_clarification_request(state: GraphState, intent: Dict[str, Any], draft_risks: List[Dict]) -> None:
    """Handle cases where user intent is unclear"""
    
    risks_list = format_risks_for_display(draft_risks)
    
    state.response = f"""I'm not sure what you'd like to do. Here are your current risks:

{risks_list}

You can do ONE of these operations:
• Update a field: "Change the likelihood of risk 1 to high"
• Remove a risk: "Remove risk 2" 
• Approve a risk: "Approve risk 1"
• Finalize all: "These all look good, proceed"

What single operation would you like to do?"""
    
    state.current_node = "complete"  # Don't loop back to risk_reviewer
    state.show_risks = True  # Signal frontend to show risks
    state.requires_input = True

async def show_current_risks_for_review(state: GraphState, draft_risks: List[Dict]) -> None:
    """Show current risks and ask for user action"""
    
    risks_display = format_risks_for_display(draft_risks)
    
    state.response = f"""Here are your current risks:

{risks_display}

You can do ONE of these operations:
• Update a field: "Change the likelihood of risk 1 to high"
• Remove a risk: "Remove the third risk"
• Approve a risk: "Approve risk 2"
• Finalize all: "These all look good, let's proceed"

What would you like to do?"""
    
    state.current_node = "complete"  # Don't loop back to risk_reviewer
    state.show_risks = True  # Signal frontend to show risks
    state.requires_input = True

def find_risk_by_identifier(draft_risks: List[Dict], identifier: str) -> tuple[Optional[Dict], Optional[int]]:
    """Find a risk by various identifiers (ID, description snippet, number)"""
    
    if not identifier:
        return None, None
    
    identifier_lower = identifier.lower()
    
    # Try to find by risk_id
    for i, risk in enumerate(draft_risks):
        if risk.get("risk_id", "").lower() == identifier_lower:
            return risk, i
    
    # Try to find by number (risk 1, risk 2, etc.)
    number_match = re.search(r'risk\s*(\d+)', identifier_lower)
    if number_match:
        try:
            risk_number = int(number_match.group(1)) - 1  # Convert to 0-based index
            if 0 <= risk_number < len(draft_risks):
                return draft_risks[risk_number], risk_number
        except (ValueError, IndexError):
            pass
    
    # Try to find by partial description match
    for i, risk in enumerate(draft_risks):
        description = risk.get("risk_description", "").lower()
        if identifier_lower in description and len(identifier_lower) > 3:  # Avoid tiny matches
            return risk, i
    
    return None, None

def format_risks_for_display(draft_risks: List[Dict]) -> str:
    """Format risks for user-friendly display"""
    
    if not draft_risks:
        return "No risks available."
    
    formatted = []
    for i, risk in enumerate(draft_risks, 1):
        risk_id = risk.get("risk_id", f"risk_{i}")
        description = risk.get("risk_description", "No description")
        likelihood = risk.get("likelihood", "Not set")
        impact = risk.get("impact", "Not set")
        is_approved = "✅ Approved" if risk.get("is_approved") else "⏳ Pending"
        
        formatted.append(f"""Risk {i} ({risk_id}) - {is_approved}:
  Description: {description}
  Likelihood: {likelihood}
  Impact: {impact}""")
    
    return "\n\n".join(formatted)

def is_greeting_message(message: str) -> bool:
    """Check if the message is a simple greeting"""
    greeting_patterns = [
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
        "how are you", "what's up", "sup", "greetings", "hiya"
    ]
    message_lower = message.lower().strip()
    return any(pattern in message_lower for pattern in greeting_patterns) and len(message_lower) < 50

async def handle_greeting_with_risks(state: GraphState, draft_risks: List[Dict]) -> None:
    """Handle greeting messages when user has risks to review"""
    
    approved_count = sum(1 for risk in draft_risks if risk.get("is_approved", False))
    pending_count = len(draft_risks) - approved_count
    
    risks_summary = format_risks_for_display(draft_risks[:3])  # Show first 3 risks
    
    greeting_response = f"""👋 Hello! I see you have {len(draft_risks)} risks to review.

Status: {approved_count} approved, {pending_count} pending approval.

Here are your current risks:

{risks_summary}

{"..." if len(draft_risks) > 3 else ""}

You can:
• Approve a risk: "Approve risk 1"
• Update a field: "Change likelihood of risk 2 to high" 
• Remove a risk: "Remove risk 3"
• Finalize all: "These all look good, let's proceed"

What would you like to do?"""
    
    state.response = greeting_response
    state.current_node = "complete"  # Don't loop back to risk_reviewer
    state.show_risks = True
    state.requires_input = True