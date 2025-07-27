import logging
from graph.state.graph_state import GraphState
from services.report_service import generate_report_from_risks
from database.repository import session_repository
from datetime import datetime
from services.risk_summary_service import generate_risk_summary

logger = logging.getLogger(__name__)

async def report_generator_node(state: GraphState) -> GraphState:
    logger.info("REPORT_GENERATOR_NODE: Creating final report")
    
    try:
        # Debug: Log current state information
        logger.info(f"REPORT_GENERATOR_NODE: Debug - Username: {state.username}")
        logger.info(f"REPORT_GENERATOR_NODE: Debug - Session ID: {state.session_id}")
        logger.info(f"REPORT_GENERATOR_NODE: Debug - Draft risks count: {len(state.draft_risks) if state.draft_risks else 0}")
        logger.info(f"REPORT_GENERATOR_NODE: Debug - Last node: {state.resume_node}")
        logger.info(f"REPORT_GENERATOR_NODE: Debug - Has previous report: {'report_content' in state.session_data}")
        
        # Check if report was already generated in this session
        if "report_content" in state.session_data and state.session_data.get("report_content"):
            logger.info("REPORT_GENERATOR_NODE: Report already exists, displaying existing report")
            state.response = f"📊 Your risk assessment report is already available!\n\n{state.session_data.get('report_title', 'Risk Assessment Report')}\n\nThe report was generated earlier in this session and is ready for viewing and download.\n\nYou can view and download your report below."
            state.current_node = "complete"
            state.resume_node = "complete"
            state.requires_input = False
            state.error = ""
             # hide the metadata popup since report is generated
            state.show_metadata_popup = False
            state.metadata_completed = True  # Mark metadata as completed
            state.show_risks = False  # Hide risks after report generation
            # Re-display the report by ensuring it's in the session data
            await session_repository.update_graph_state(state)
            logger.info("REPORT_GENERATOR_NODE: Existing report re-displayed successfully")
            return state
        
        # Get approved risks from state
        if not state.draft_risks:
            logger.warning("REPORT_GENERATOR_NODE: No risks found in state.draft_risks")
            state.error = "No risks found in the current session. Please generate and approve some risks first before requesting a report."
            state.response = "❌ Cannot generate report: No risks found in the current session.\n\nTo generate a report, you need to:\n1. First generate some risks\n2. Review and approve the risks you want in the report\n3. Then request report generation\n\nPlease start by asking me to 'generate risks for my organization'."
            state.current_node = "complete"
            state.resume_node = "complete"
            state.requires_input = False
            await session_repository.update_graph_state(state)
            return state
            
        approved_risks = [risk for risk in state.draft_risks if risk.get("is_approved", False)]
        if not approved_risks:
            logger.warning("REPORT_GENERATOR_NODE: No approved risks found")
            state.error = "No approved risks found. Please approve some risks first before generating the report."
            state.response = "❌ Cannot generate report: No approved risks found.\n\nI found risks in your session, but none are approved yet. To generate a report:\n1. Review your current risks\n2. Approve the risks you want included in the report\n3. Then request report generation again\n\nWould you like me to show you the current risks for review?"
            state.current_node = "complete"
            state.resume_node = "complete"
            state.requires_input = False
            await session_repository.update_graph_state(state)
            return state
        
        # Generate AI-powered risk summary
        logger.info("REPORT_GENERATOR_NODE: Generating AI risk summary")
        organization_name = state.session_data.get("organization", "Organization")
        risk_summary = await generate_risk_summary(approved_risks, organization_name)
        logger.info("REPORT_GENERATOR_NODE: AI risk summary generated successfully")

        # Create report data from state information
        report_data = {
            "title": f"Risk Assessment Report - {state.username}",
            "organization": organization_name,
            "created_by": {"name": state.username},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "completed",
            "total_risks": len(approved_risks),
            "risks": approved_risks,
            "ai_summary": risk_summary
        }
        
        # Generate the report (HTML format for web display)
        report_content = await generate_report_from_risks(report_data, "html")
        
        # Store the report content in state for frontend display
        state.session_data["report_content"] = report_content
        state.session_data["report_title"] = f"{report_data['title']}"
        
        # Update state for successful report generation
        state.response = f"🎉 Your comprehensive risk assessment report has been generated successfully!\n\nReport for: {report_data['title']}\nOrganization: {report_data['organization']}\nTotal Approved Risks: {len(approved_risks)}\n\n🤖 This report includes AI-powered risk analysis with:\n• Executive Summary\n• Key Risk Findings\n• Risk Profile Analysis\n• Treatment Effectiveness Assessment\n• Strategic Recommendations\n\nYou can view and download your report below.\n\nSession complete."
        state.current_node = "complete"
        state.resume_node = "complete"  # Session ends here
        state.requires_input = False
        state.error = ""  # Clear any previous errors
        state.is_active = False  # Mark session as complete
        # hide the metadata popup since report is generated
        state.show_metadata_popup = False
        state.metadata_completed = True  # Mark metadata as completed
        state.show_risks = False  # Hide risks after report generation
        logger.info(f"REPORT_GENERATOR_NODE: Report generated successfully, setting state to complete")
        # Keep all other state data for potential future reference
        
        # Save state after report generation
        await session_repository.update_graph_state(state)
        logger.info("State updated after report generation")
        
    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}")
        state.error = f"Report generation failed: {str(e)}"
        state.response = "❌ Sorry, I encountered an error generating the report.\n\nThis could be due to:\n• Issues with the AI analysis service\n• Problems with report formatting\n• Network connectivity issues\n\nPlease try again in a moment, or ask me to help with something else."
        state.current_node = "complete"  # End the workflow instead of looping
        state.resume_node = "complete"
        state.requires_input = False  # Don't require input, just end
        
        try:
            await session_repository.update_graph_state(state)
        except Exception as save_error:
            logger.error(f"Failed to save error state: {str(save_error)}")
    
    return state