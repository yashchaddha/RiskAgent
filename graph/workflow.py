"""
Main Langraph workflow definition
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from graph.state.graph_state import GraphState
from graph.nodes.auth_node import auth_node
from graph.nodes.intent_parser_node import intent_parser_node
from graph.nodes.knowledge_engine_node import knowledge_engine_node
from graph.nodes.risk_generator_node import risk_generator_node
from graph.nodes.risk_reviewer_node import risk_reviewer_node
from graph.nodes.metadata_collector_node import metadata_collector_node
from graph.nodes.database_manager_node import database_manager_node
from graph.nodes.report_generator_node import report_generator_node
import logging

logger = logging.getLogger(__name__)

# Compile workflow once at module import
def create_workflow():
    global _compiled_workflow
    try:
        return _compiled_workflow
    except NameError:
        logger.info("🚀 WORKFLOW: Creating Langraph StateGraph workflow")
        workflow = StateGraph(GraphState)
        
        # Register nodes
        workflow.add_node("auth", auth_node)
        workflow.add_node("intent_parser", intent_parser_node)
        workflow.add_node("knowledge_engine", knowledge_engine_node)
        workflow.add_node("risk_generator", risk_generator_node)
        workflow.add_node("risk_reviewer", risk_reviewer_node)
        workflow.add_node("metadata_collector", metadata_collector_node)
        workflow.add_node("database_manager", database_manager_node)
        workflow.add_node("report_generator", report_generator_node)

        # Entry point
        workflow.set_entry_point("auth")

        # Conditional routing
        workflow.add_conditional_edges(
            "auth",
            route_from_auth,
            {
                "intent_parser": "intent_parser"
            }
        )
        workflow.add_conditional_edges(
            "intent_parser",
            route_from_intent_parser,
            {
                "knowledge_engine": "knowledge_engine",
                "risk_generator": "risk_generator",
                "risk_reviewer": "risk_reviewer",
                "metadata_collector": "metadata_collector",
                "database_manager": "database_manager",
                "report_generator": "report_generator",
                "complete": END
            }
        )
        workflow.add_conditional_edges(
            "knowledge_engine",
            route_from_knowledge_engine,
            {
                "risk_generator": "risk_generator",
                "risk_reviewer": "risk_reviewer",
                "intent_parser": "intent_parser",
                "complete": END
            }
        )
        workflow.add_conditional_edges(
            "risk_generator",
            route_from_risk_generator,
            {
                "risk_reviewer": "risk_reviewer",
                "intent_parser": "intent_parser",
                "complete": END
            }
        )
        workflow.add_conditional_edges(
            "risk_reviewer",
            route_from_risk_reviewer,
            {
                "risk_generator": "risk_generator",
                "metadata_collector": "metadata_collector",
                "database_manager": "database_manager",
                "risk_reviewer": "risk_reviewer",
                "intent_parser": "intent_parser",
                "complete": END
            }
        )
        workflow.add_conditional_edges(
            "metadata_collector",
            route_from_metadata_collector,
            {
                "database_manager": "database_manager", 
                "risk_reviewer": "risk_reviewer", 
                "metadata_collector": "metadata_collector"
            }
        )
        workflow.add_conditional_edges(
            "database_manager",
            route_from_database_manager,
            {
                "report_generator": "report_generator", 
                "risk_reviewer": "risk_reviewer", 
                "database_manager": "database_manager", 
                "intent_parser": "intent_parser",
                "complete": END
            }
        )
        workflow.add_conditional_edges(
            "report_generator",
            route_from_report_generator,
            {
                "report_generator": "report_generator", 
                "intent_parser": "intent_parser", 
                "complete": END
            }
        )

        logger.info("🚀 WORKFLOW: Compiling Langraph workflow")
        _compiled_workflow = workflow.compile()
        return _compiled_workflow

# Execute workflow per message
async def execute_workflow(state: GraphState) -> GraphState:
    logger.info("🚀 WORKFLOW: Starting execution at node: %s", state.current_node)
    workflow = create_workflow()
    new_state_dict = await workflow.ainvoke(state)
    # Convert dict back to GraphState object
    new_state = GraphState(**new_state_dict) if isinstance(new_state_dict, dict) else new_state_dict
    logger.info("🚀 WORKFLOW: Execution completed, next node: %s", new_state.current_node)
    
    # Note: State is now saved by individual nodes, not here
    return new_state

# Routing functions

def route_from_auth(state: GraphState) -> str:
    # Always route to intent_parser - let it handle context-aware routing
    next_node = "intent_parser"
    logger.debug(f"Routing from auth -> {next_node}")
    return next_node

def route_from_intent_parser(state: GraphState) -> str:
    valid = {"knowledge_engine", "risk_generator", "risk_reviewer", "metadata_collector", "database_manager", "report_generator", "complete"}
    target = state.current_node if state.current_node in valid else "complete"
    logger.debug(f"Routing from intent_parser -> {target}")
    return target

def route_from_knowledge_engine(state: GraphState) -> str:
    mapping = {
        "risk_generator": "risk_generator", 
        "risk_reviewer": "risk_reviewer", 
        "intent_parser": "intent_parser", 
        "complete": "complete"
    }
    target = mapping.get(state.current_node, "complete")
    logger.debug(f"Routing from knowledge_engine -> {target}")
    return target

def route_from_risk_generator(state: GraphState) -> str:
    valid = {"risk_reviewer", "intent_parser", "complete"}
    target = state.current_node if state.current_node in valid else "intent_parser"
    logger.debug(f"Routing from risk_generator -> {target}")
    return target

def route_from_risk_reviewer(state: GraphState) -> str:
    valid = {"risk_generator", "metadata_collector", "database_manager", "risk_reviewer", "complete"}
    target = state.current_node if state.current_node in valid else "intent_parser"
    logger.debug(f"Routing from risk_reviewer -> {target}")
    return target

def route_from_metadata_collector(state: GraphState) -> str:
    mapping = {
        "database_manager": "database_manager", 
        "risk_reviewer": "risk_reviewer"
    }
    target = mapping.get(state.current_node, "complete")
    logger.debug(f"Routing from metadata_collector -> {target}")
    return target

def route_from_database_manager(state: GraphState) -> str:
    mapping = {
        "report_generator": "report_generator", 
        "risk_reviewer": "risk_reviewer", 
        "database_manager": "database_manager",
        "complete": "complete",
    }
    target = mapping.get(state.current_node, "complete")
    logger.debug(f"Routing from database_manager -> {target}")
    return target

def route_from_report_generator(state: GraphState) -> str:
    mapping = {
        "report_generator": "report_generator", 
        "intent_parser": "intent_parser"
    }
    target = mapping.get(state.current_node, "complete")
    logger.debug(f"Routing from report_generator -> {target}")
    return target
