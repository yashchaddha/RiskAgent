import logging
from graph.state.graph_state import GraphState
from database.repository import session_repository

logger = logging.getLogger(__name__)

async def metadata_collector_node(state: GraphState) -> GraphState:
    logger.info("METADATA_COLLECTOR_NODE: Processing metadata save request")
    
    try:
        # This node should only be called when saving metadata, not for triggering popup
        # The popup is now triggered automatically when all risks are approved
        
        # Check if we have approved risks with metadata
        approved_risks = [risk for risk in state.draft_risks if risk.get("is_approved", False)]
        
        if not approved_risks:
            state.response = "No approved risks found. Please approve some risks first."
            state.current_node = "complete"
            state.requires_input = True
            state.error = ""
            await session_repository.update_graph_state(state)
            return state
        
        # Check if metadata has been collected
        risks_with_metadata = [risk for risk in approved_risks if risk.get("asset_value") is not None]
        
        if len(risks_with_metadata) == len(approved_risks):
            # All approved risks have metadata - proceed to report generation
            state.response = "✅ All metadata has been collected successfully! Generating your comprehensive risk assessment report..."
            state.current_node = "report_generator"
            state.resume_node = "report_generator"
            state.requires_input = False
            state.error = ""
            state.metadata_completed = True  # Mark metadata as completed
            state.show_metadata_popup = False  # Hide popup since completed
            
            logger.info(f"Metadata collection complete for {len(approved_risks)} risks. Proceeding to report generation.")
        else:
            # Some risks still missing metadata
            missing_count = len(approved_risks) - len(risks_with_metadata)
            state.response = f"⚠️ {missing_count} risk(s) still need metadata. Please complete the metadata form for all approved risks."
            state.current_node = "complete"
            state.show_metadata_popup = True  # Show popup again
            state.show_risks = True
            state.requires_input = True
            state.error = ""
        
        # Save state
        await session_repository.update_graph_state(state)
        logger.info("State updated after metadata collection check")
        
    except Exception as e:
        logger.error(f"Failed to process metadata collection: {str(e)}")
        state.error = f"Metadata collection failed: {str(e)}"
        state.response = "Sorry, I encountered an error processing metadata. Please try again."
        state.current_node = "complete"
        state.requires_input = True
        
        try:
            await session_repository.update_graph_state(state)
        except Exception as save_error:
            logger.error(f"Failed to save error state: {str(save_error)}")
    
    return state