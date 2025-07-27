import logging
from graph.state.graph_state import GraphState
from graph.tools.llm_tools import generate_risks_llm
from database.repository import session_repository
from config.constants import DEFAULT_ORG_CONTEXT
from models.risk_model import RiskValueWeight

logger = logging.getLogger(__name__)

def convert_risk_value_to_weight(value_str: str) -> dict:
    """Convert string risk value to RiskValueWeight dict format"""
    value_mapping = {
        "very low": {"value": "Very Low", "weight": 1},
        "low": {"value": "Low", "weight": 2},
        "medium": {"value": "Medium", "weight": 3},
        "high": {"value": "High", "weight": 4},
        "very high": {"value": "Very High", "weight": 5}
    }
    return value_mapping.get(value_str.lower(), {"value": value_str, "weight": 3})

async def risk_generator_node(state: GraphState) -> GraphState:
    logger.info("RISK_GENERATOR_NODE: Generating risks via LLM")
    
    try:
        drafts = await generate_risks_llm(DEFAULT_ORG_CONTEXT)
        
        # Add risk_id to each draft risk if not present and convert likelihood/impact to proper format
        for i, risk in enumerate(drafts):
            if 'risk_id' not in risk:
                risk['risk_id'] = f"R-{i+1:03d}"  # R-001, R-002, etc.
            
            # Convert likelihood and impact strings to RiskValueWeight objects
            if isinstance(risk.get('likelihood'), str):
                risk['likelihood'] = convert_risk_value_to_weight(risk['likelihood'])
            if isinstance(risk.get('impact'), str):
                risk['impact'] = convert_risk_value_to_weight(risk['impact'])
            
            # Initialize approval status for frontend
            risk['is_approved'] = False
        
        # Update state attributes
        state.draft_risks = drafts  # list of dicts
        state.selected_risk_ids = [r['risk_id'] for r in drafts]  # All selected by default
        state.show_risks = True  # Signal frontend to show risks
        state.error = ""  # Clear any previous errors
        
        # build checklist response text
        table = "Here are your draft risks (all selected by default):\n"
        for r in drafts:
            table += f"- {r['risk_id']}: {r['risk_description']}\n"

        state.response = table + "\nYou can uncheck, edit, or add more risks."
        state.current_node = "complete"
        state.resume_node = "complete"  # Update resume point
        state.requires_input = True
        # Keep intent from previous node
        
        # Save state after risk generation
        logger.info(f"🆔 Risk generator state ID: {state.id}")
        update_success = await session_repository.update_graph_state(state)
        logger.info(f"💾 Risk generator update result: {update_success}")
        if update_success:
            logger.info("✅ State updated after risk generation")
        else:
            logger.error("❌ Failed to update state after risk generation")
        
    except Exception as e:
        logger.error(f"Failed to generate risks: {str(e)}")
        state.error = f"Risk generation failed: {str(e)}"
        state.response = "Sorry, I encountered an error generating risks. Please try again."
        state.current_node = "intent_parser"  # Go back to intent parser on error
        state.requires_input = True
        
        try:
            await session_repository.update_graph_state(state)
        except Exception as save_error:
            logger.error(f"Failed to save error state: {str(save_error)}")
    
    return state