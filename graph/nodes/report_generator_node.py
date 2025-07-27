import logging
from graph.state.graph_state import GraphState
from services.report_service import generate_report
from database.repository import session_repository

logger = logging.getLogger(__name__)

async def report_generator_node(state: GraphState) -> GraphState:
    logger.info("REPORT_GENERATOR_NODE: Creating final report")
    
    try:
        report_url = await generate_report(state.username, state.session_data)
        
        # Update state for successful report generation
        state.response = f"🎉 Your report is ready: {report_url}" + "\nSession complete."
        state.current_node = "complete"
        state.resume_node = "complete"  # Session ends here
        state.requires_input = False
        state.error = ""  # Clear any previous errors
        state.is_active = False  # Mark session as complete
        # Keep all other state data for potential future reference
        
        # Save state after report generation
        await session_repository.update_graph_state(state)
        logger.info("State updated after report generation")
        
    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}")
        state.error = f"Report generation failed: {str(e)}"
        state.response = "Sorry, I encountered an error generating the report. Please try again."
        state.current_node = "report_generator"
        state.resume_node = "report_generator"
        state.requires_input = True
        
        try:
            await session_repository.update_graph_state(state)
        except Exception as save_error:
            logger.error(f"Failed to save error state: {str(save_error)}")
    
    return state