import logging
from typing import Dict, Any
from graph.state.graph_state import GraphState
from database.repository import session_repository

logger = logging.getLogger(__name__)

async def database_manager_node(state: GraphState) -> GraphState:
    logger.info("DATABASE_MANAGER_NODE: Processing database operations")
    
    try:
        # Check if there's a pending operation from risk_reviewer
        pending_op = state.session_data.get("pending_operation")
        
        if pending_op:
            # Handle risk-specific operations (update, remove, approve)
            await handle_risk_operation(state, pending_op)
        else:
            # No pending operation - this shouldn't happen in normal flow
            state.response = "No operation to process. Returning to risk review."
            state.current_node = "complete"
            state.requires_input = True
            
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}")
        state.error = f"Database operation failed: {str(e)}"
        state.response = f"Error processing request: {e}. Please try again."
        state.current_node = "risk_reviewer"  # Go back to risk reviewer on error
        state.resume_node = "risk_reviewer"
        state.requires_input = True
    
    # Save state after database operations
    try:
        await session_repository.update_graph_state(state)
        logger.info("State updated after database operations")
    except Exception as save_error:
        logger.error(f"Failed to update state: {str(save_error)}")
        if not state.error:
            state.error = f"State save failed: {str(save_error)}"
    
    return state

async def handle_risk_operation(state: GraphState, operation: Dict[str, Any]) -> None:
    """Handle specific risk operations (update, remove, approve)"""
    
    operation_type = operation.get("operation")
    
    if operation_type == "update_risk":
        await update_risk_field(state, operation)
    elif operation_type == "remove_risk":
        await remove_risk(state, operation)
    elif operation_type == "approve_risk":
        await approve_risk(state, operation)
    else:
        raise ValueError(f"Unknown operation type: {operation_type}")
    
    # Clear the pending operation
    state.session_data.pop("pending_operation", None)

async def update_risk_field(state: GraphState, operation: Dict[str, Any]) -> None:
    """Update a specific field of a risk"""
    
    risk_index = operation.get("risk_index")
    field = operation.get("field")
    new_value = operation.get("new_value")
    
    logger.info(f"Updating risk {risk_index}, field '{field}' to '{new_value}'")
    
    # Validate inputs
    if risk_index is None or risk_index < 0 or risk_index >= len(state.draft_risks):
        raise ValueError(f"Invalid risk index: {risk_index}")
    
    if not field:
        raise ValueError("Field to update not specified")
    
    # Validate field name
    allowed_fields = ["likelihood", "impact", "risk_description", "mitigation_strategy"]
    if field not in allowed_fields:
        raise ValueError(f"Field '{field}' is not allowed. Allowed fields: {allowed_fields}")
    
    # Get the risk to update
    risk = state.draft_risks[risk_index]
    old_value = risk.get(field, "Not set")
    
    # Update the field in the draft_risks list (direct field in GraphState)
    state.draft_risks[risk_index][field] = new_value
    
    logger.info(f"Updated risk {risk.get('risk_id', 'unknown')} - {field}: '{old_value}' → '{new_value}'")
    
    # Set response and routing
    state.response = f"✅ Updated {field} from '{old_value}' to '{new_value}'.\n\nWhat else would you like to do?"
    # remove the pending operation
    state.session_data.pop("pending_operation", None)
    state.current_node = "complete"  # Go back to reviewer for more operations
    state.resume_node = "complete"
    state.requires_input = True

async def remove_risk(state: GraphState, operation: Dict[str, Any]) -> None:
    """Remove a risk completely"""
    
    risk_index = operation.get("risk_index")
    
    logger.info(f"Removing risk at index {risk_index}")
    
    # Validate input
    if risk_index is None or risk_index < 0 or risk_index >= len(state.draft_risks):
        raise ValueError(f"Invalid risk index: {risk_index}")
    
    # Get risk info before removal
    risk_to_remove = state.draft_risks[risk_index]
    risk_description = risk_to_remove.get("risk_description", "Unknown risk")
    
    # Remove from draft_risks (direct field in GraphState)
    state.draft_risks.pop(risk_index)
    
    logger.info(f"Removed risk: {risk_description}")
    
    # Set response and routing
    remaining_count = len(state.draft_risks)
    
    if remaining_count == 0:
        state.response = f"✅ Removed risk: '{risk_description}'.\n\nYou have no risks remaining. Would you like to generate new risks?"
        state.current_node = "intent_parser"
        state.requires_input = True
    else:
        state.response = f"✅ Removed risk: '{risk_description}'.\n\nWhat would you like to do next?"
        state.current_node = "complete"  # Go back to complete
        state.resume_node = "complete"
        # remove the pending operation
        state.session_data.pop("pending_operation", None)
        state.show_risks = True  # Signal frontend to show updated risks
        state.requires_input = True

async def approve_risk(state: GraphState, operation: Dict[str, Any]) -> None:
    """Approve a specific risk by adding is_approved=True"""
    
    risk_index = operation.get("risk_index")
    
    logger.info(f"Approving risk at index {risk_index}")
    
    # Validate input
    if risk_index is None or risk_index < 0 or risk_index >= len(state.draft_risks):
        raise ValueError(f"Invalid risk index: {risk_index}")
    
    # Get risk info
    risk = state.draft_risks[risk_index]
    risk_description = risk.get("risk_description", "Unknown risk")
    
    # Add is_approved flag to the risk
    state.draft_risks[risk_index]["is_approved"] = True
    
    logger.info(f"Approved risk: {risk_description}")
    
    # Check if all risks are approved
    all_approved = all(risk.get("is_approved", False) for risk in state.draft_risks)
    
    if all_approved:
        # All risks approved - check if metadata already completed
        if not state.metadata_completed:
            # Show metadata popup only if not already completed
            state.response = f"✅ Approved risk: '{risk_description}'.\n\n🎉 All risks are now approved!\n\n📋 The metadata collection form will open automatically. Please provide additional details for each risk to complete your assessment."
            state.show_metadata_popup = True  # Automatically trigger metadata popup
        else:
            # Metadata already completed - proceed directly to report
            state.response = f"✅ Approved risk: '{risk_description}'.\n\n🎉 All risks are now approved!\n\n📊 Since metadata is already completed, proceeding to report generation..."
            state.current_node = "report_generator"
            state.resume_node = "report_generator"
            state.requires_input = False
        
        state.risks_approved = True
        state.show_risks = True  # Also show risks
        from datetime import datetime
        state.approval_timestamp = datetime.utcnow()
    else:
        # Some risks still pending
        pending_count = sum(1 for risk in state.draft_risks if not risk.get("is_approved", False))
        state.response = f"✅ Approved risk: '{risk_description}'.\n\nYou have {pending_count} risk(s) still pending approval. What would you like to do next?"

    state.current_node = "complete"  # Go back to complete
    state.resume_node = "complete"
    # remove the pending operation
    state.session_data.pop("pending_operation", None)
    state.requires_input = True

def format_updated_risks_summary(risks: list) -> str:
    """Format a summary of current risks after updates"""
    
    if not risks:
        return "No risks remaining."
    
    summary = f"Current risks ({len(risks)} total):"
    for i, risk in enumerate(risks, 1):
        approval_status = "✅ Approved" if risk.get("is_approved", False) else "⏳ Pending"
        summary += f"\n{i}. {risk.get('risk_description', 'No description')} - {approval_status}"
        summary += f"\n   Likelihood: {risk.get('likelihood', 'Not set')}, Impact: {risk.get('impact', 'Not set')}"
    
    return summary