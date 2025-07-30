from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from graph.state.graph_state import RiskAgentState, get_state_summary
from graph.nodes.auth import authentication_node, session_initialization_node, logout_node
from graph.nodes.welcome import welcome_node, intent_classification_node, conversation_handler_node
from graph.nodes.risk_generation import risk_generation_node, view_risks_node
from graph.nodes.qa import general_qa_node, help_node
from graph.nodes.report import (matrix_update_node, report_generation_node)
from config import get_logger, settings
from models.models import UserStage

logger = get_logger(__name__)

class RiskManagementWorkflow:
    def __init__(self):
        self.workflow = None
        self.checkpointer = MemorySaver()  # LangGraph's built-in memory
        self._build_workflow()
    
    def _build_workflow(self):
        """Build the LangGraph StateGraph workflow"""
        
        logger.info("Building Risk Management Agent workflow...")
        
        # Create StateGraph with our state schema
        workflow = StateGraph(RiskAgentState)
        
        # Add all nodes
        self._add_nodes(workflow)
        
        # Add edges and routing logic
        self._add_edges(workflow)
        
        # Compile workflow with checkpointer for memory
        self.workflow = workflow.compile(
            checkpointer=self.checkpointer
            # Removed HITL checkpoint - reports now generate directly
        )
        
        logger.info("Workflow compiled successfully with memory checkpointer")
    
    def _add_nodes(self, workflow: StateGraph):
        """Add all nodes to the workflow"""
        
        # Authentication and session management
        workflow.add_node("authentication", authentication_node)
        workflow.add_node("session_init", session_initialization_node)
        workflow.add_node("logout", logout_node)
        
        # Core conversation flow
        workflow.add_node("welcome", welcome_node)
        workflow.add_node("intent_classification", intent_classification_node)
        workflow.add_node("conversation_handler", conversation_handler_node)
        
        # Risk management nodes
        workflow.add_node("risk_generation", risk_generation_node)
        workflow.add_node("view_risks", view_risks_node)
        
        # General interaction nodes
        workflow.add_node("general_qa", general_qa_node)
        workflow.add_node("matrix_update", matrix_update_node)
        workflow.add_node("help", help_node)
        
        # Report generation (direct, no HITL)
        workflow.add_node("report_generation", report_generation_node)
        
        # Error handling node
        workflow.add_node("error_handler", self._error_handler_node)
        
        logger.info("Added all workflow nodes")
    
    def _add_edges(self, workflow: StateGraph):
        """Add edges and routing logic to the workflow"""
        
        # Entry point routing - determine if this is login/register or regular message
        workflow.add_conditional_edges(
            START,
            self._route_entry_point,
            {
                "login_register": "session_init",
                "regular_message": "intent_classification"
            }
        )
        
        # After session_init (login/register), always go to welcome
        workflow.add_edge("session_init", "welcome")
        
        # After welcome, go to intent_classification
        workflow.add_edge("welcome", "intent_classification")
        
        # Main conversation loop
        workflow.add_edge("intent_classification", "conversation_handler")
        
        # Intent-based routing from conversation_handler
        workflow.add_conditional_edges(
            "conversation_handler",
            self._route_by_intent,
            {
                "general_question": "general_qa",
                "change_matrix": "matrix_update", 
                "generate_risks": "risk_generation",
                "view_risks": "view_risks",
                "generate_report": "report_generation",
                "help": "help",
                "logout": "logout",
                "error": "error_handler"
            }
        )
        
        # Return to intent classification after most actions, or END for completed responses
        workflow.add_edge("general_qa", END)  # End after answering general questions
        workflow.add_edge("matrix_update", END)
        workflow.add_edge("view_risks", END)
        workflow.add_edge("help", END)  # End after providing help
        
        # Risk generation flow - end after generating risks, user can continue with new message
        workflow.add_edge("risk_generation", END)
        
        # Direct report generation (removed HITL approval)
        
        # Final states
        workflow.add_edge("report_generation", END)
        workflow.add_edge("logout", END)
        workflow.add_edge("error_handler", "intent_classification")
        
        logger.info("Added all workflow edges and routing logic")
    
    def _route_by_intent(self, state: RiskAgentState) -> str:
        """Route based on current user intent"""
        
        current_intent = state.get("current_intent")
        error_message = state.get("error_message")
        
        # Handle errors first
        if error_message:
            logger.warning(f"Routing to error handler: {error_message}")
            return "error"
        
        # Handle logout
        if current_intent == "logout":
            return "logout"
        
        # Handle help requests
        if current_intent == "help" or (current_intent == "general_question" and 
                                       any(word in state.get("messages", [])[-1].content.lower() 
                                           for word in ["help", "how to", "what can you do"])):
            return "help"
        
        # Standard intent routing
        intent_mapping = {
            "general_question": "general_question",
            "change_matrix": "change_matrix",
            "generate_risks": "generate_risks", 
            "view_risks": "view_risks",
            "generate_report": "generate_report",
            "approve_report": "approve_report",
            "reject_report": "reject_report"
        }
        
        route = intent_mapping.get(current_intent, "general_question")
        logger.info(f"Routing intent '{current_intent}' to '{route}'")
        
        return route
    
        
    def _route_entry_point(self, state: RiskAgentState) -> str:
        """Determine if this is a login/register action or a regular message"""
        
        action = state.get("action")
        user_id = state.get("user_id")
        temp_data = state.get("temp_data", {})
        messages = state.get("messages", [])
        
        # If this is a login or register action, go through session_init and welcome
        if action in ["login", "register"]:
            logger.info(f"Login/Register action detected - routing to session_init")
            return "login_register"
        
        # If user is authenticated and there are existing messages, this is a regular chat message
        if user_id and temp_data.get("session_initialized") and messages:
            logger.info(f"Regular message for authenticated user {user_id} - routing to intent_classification")
            return "regular_message"
        
        # Default to regular_message for safety (most cases should be regular messages)
        logger.info(f"Default routing to intent_classification")
        return "regular_message"
    
    async def _error_handler_node(self, state: RiskAgentState) -> Dict[str, Any]:
        """Handle errors and provide recovery options"""
        
        user_id = state.get("user_id")
        error_message = state.get("error_message", "Unknown error occurred")
        retry_count = state.get("retry_count", 0)
        
        logger.error(f"Error handler called for user {user_id}: {error_message} (retry: {retry_count})")
        
        if retry_count > 3:
            # Too many retries, reset to welcome
            recovery_message = """I'm experiencing technical difficulties. Let me reset and we can start fresh.

What would you like to do?
• Generate risks for your organization
• Ask questions about risk management
• View your existing risks

How can I help you today?"""
            
            return {
                "current_stage": UserStage.WELCOME,
                "current_intent": None,
                "error_message": None,
                "retry_count": 0,
                "messages": state.get("messages", []) + [
                    {"role": "assistant", "content": recovery_message}
                ],
                "last_action": "error_recovery_reset"
            }
        
        else:
            # Provide helpful error message and continue
            recovery_message = """I encountered a temporary issue, but I'm back now! 

Your progress has been saved. What would you like to do next?
• Continue with your risk assessment
• Ask me any questions
• Get help with the current step

How can I assist you?"""
            
            return {
                "error_message": None,
                "retry_count": retry_count + 1,
                "messages": state.get("messages", []) + [
                    {"role": "assistant", "content": recovery_message}
                ],
                "last_action": f"error_recovery_attempt_{retry_count + 1}"
            }
    
    def get_workflow(self):
        """Get the compiled workflow"""
        return self.workflow
    
    def get_checkpointer(self):
        """Get the memory checkpointer"""
        return self.checkpointer
    
    async def invoke_workflow(self, input_data: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        """Invoke the workflow with thread-based memory"""
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            logger.info(f"Invoking workflow for thread: {thread_id}")
            state_summary = get_state_summary(input_data)
            logger.info(f"Input state summary: {state_summary}")
            
            result = await self.workflow.ainvoke(input_data, config)
            
            result_summary = get_state_summary(result)
            logger.info(f"Output state summary: {result_summary}")
            
            return result
            
        except Exception as e:
            logger.error(f"Workflow invocation error: {e}", exc_info=True)
            raise
    
    async def stream_workflow(self, input_data: Dict[str, Any], thread_id: str):
        """Stream workflow execution for real-time updates"""
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            logger.info(f"Streaming workflow for thread: {thread_id}")
            
            async for chunk in self.workflow.astream(input_data, config):
                yield chunk
                
        except Exception as e:
            logger.error(f"Workflow streaming error: {e}", exc_info=True)
            raise
    
    async def get_state(self, thread_id: str) -> Dict[str, Any]:
        """Get current state for a thread"""
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            state = await self.workflow.aget_state(config)
            return state.values if state else {}
            
        except Exception as e:
            logger.error(f"Get state error: {e}", exc_info=True)
            return {}
    
    async def update_state(self, thread_id: str, state_update: Dict[str, Any]) -> bool:
        """Update state for a thread"""
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            await self.workflow.aupdate_state(config, state_update)
            logger.info(f"State updated for thread: {thread_id}")
            return True
            
        except Exception as e:
            logger.error(f"Update state error: {e}", exc_info=True)
            return False

# Global workflow instance
risk_workflow = RiskManagementWorkflow()

# Convenience functions for easy access
async def invoke_risk_workflow(input_data: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
    """Invoke the risk management workflow"""
    return await risk_workflow.invoke_workflow(input_data, thread_id)

async def stream_risk_workflow(input_data: Dict[str, Any], thread_id: str):
    """Stream the risk management workflow"""
    async for chunk in risk_workflow.stream_workflow(input_data, thread_id):
        yield chunk

async def get_workflow_state(thread_id: str) -> Dict[str, Any]:
    """Get current workflow state"""
    return await risk_workflow.get_state(thread_id)

async def update_workflow_state(thread_id: str, state_update: Dict[str, Any]) -> bool:
    """Update workflow state"""
    return await risk_workflow.update_state(thread_id, state_update)