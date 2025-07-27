import logging
import json
from typing import Dict, Any
from graph.state.graph_state import GraphState
from database.repository import session_repository
from config.settings import settings
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key)

async def intent_parser_node(state: GraphState) -> GraphState:
    logger.info("INTENT_PARSER_NODE: Analyzing message with full context")
    
    try:
        # Use context-aware intent classification
        routing_decision = await analyze_context_and_route(state)
        
        # Update state based on LLM decision
        state.intent = routing_decision.get("intent", "other")
        state.current_node = routing_decision.get("next_node", "knowledge_engine")
        state.error = ""  # Clear any previous errors
        state.response = ""
        state.resume_node = state.current_node
        state.requires_input = False
        
        # Set show_risks flag based on routing decision
        if routing_decision.get("show_risks", False):
            state.show_risks = True
        
        logger.info(f"🧠 Context-aware routing: {state.user_message[:50]}... -> {state.current_node} (intent: {state.intent})")
        
        # Save state
        logger.info(f"🆔 Intent parser state ID: {state.id}")
        update_success = await session_repository.update_graph_state(state)
        logger.info(f"💾 Intent parser update result: {update_success}")
        
    except Exception as e:
        logger.error(f"Failed to parse intent with context: {str(e)}")
        state.error = f"Intent parsing failed: {str(e)}"
        state.current_node = "knowledge_engine"  # Safe fallback
        state.intent = "error"
    
    return state

async def analyze_context_and_route(state: GraphState) -> Dict[str, Any]:
    """Use LLM to analyze full context and determine routing"""
    
    # Build comprehensive context for LLM
    context = {
        "user_message": state.user_message,
        "has_draft_risks": bool(state.draft_risks and len(state.draft_risks) > 0),
        "draft_risks_count": len(state.draft_risks) if state.draft_risks else 0,
        "approved_risks_count": sum(1 for risk in (state.draft_risks or []) if risk.get("is_approved", False)),
        "risks_approved": state.risks_approved,
        "metadata_completed": state.metadata_completed,
        "current_intent": state.intent,
        "last_node": state.resume_node,
        "metadata_pending": bool(state.metadata_pending and len(state.metadata_pending) > 0),
        "authenticated": state.authenticated,
        "session_active": state.is_active
    }
    
    # Sample of risks for context
    risk_samples = []
    if state.draft_risks:
        for i, risk in enumerate(state.draft_risks[:3]):
            risk_samples.append({
                "risk_id": risk.get("risk_id", f"R-{i+1:03d}"),
                "description": risk.get("risk_description", "")[:100],
                "is_approved": risk.get("is_approved", False)
            })
    
    prompt = f"""
Analyze this user message and route to the correct workflow node.

USER MESSAGE: "{state.user_message}"
HAS RISKS: {context['has_draft_risks']} (total: {context['draft_risks_count']}, approved: {context['approved_risks_count']})
METADATA COMPLETED: {context['metadata_completed']}

ROUTING RULES:
- Greetings (hi, hello) → knowledge_engine
- Risk commands (approve R-001, change likelihood) + has risks → risk_reviewer  
- Risk commands + no risks → knowledge_engine
- Generate/create risks → risk_generator
- Report generation requests (metadata already completed) → report_generator
  * "proceed to report", "generate report", "create report" + metadata_completed=True
- Metadata collection requests (metadata not completed) → metadata_collector
  * "save metadata", "done with metadata" + metadata_completed=False
- Help/questions → knowledge_engine
- Exit/bye → complete

Return JSON only:
{{
    "intent": "greeting|help|generate_risks|review_risks|report_generation|metadata_collection|other",
    "next_node": "knowledge_engine|risk_generator|risk_reviewer|report_generator|metadata_collector|complete",
    "show_risks": {str(context['has_draft_risks']).lower()},
    "confidence": 0.9
}}"""
    
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a precise workflow router. Analyze context carefully and respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        logger.info(f"🤖 Raw LLM response: {content}")
        
        # Clean up response if it has markdown formatting
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        # Try to parse JSON
        result = json.loads(content)
        logger.info(f"✅ Parsed LLM routing decision: {result}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}. Raw content: '{content if 'content' in locals() else 'No content'}'")
        # Try to extract intent from failed response
        fallback_intent = extract_fallback_intent(state.user_message, state.draft_risks)
        return fallback_intent
        
    except Exception as e:
        logger.error(f"Failed to get LLM routing decision: {e}")
        # Safe fallback
        fallback_intent = extract_fallback_intent(state.user_message, state.draft_risks)
        return fallback_intent

def extract_fallback_intent(user_message: str, draft_risks: list) -> dict:
    """Extract intent using simple rules when LLM fails"""
    message_lower = user_message.lower().strip()
    
    # Simple pattern matching for common cases
    if any(word in message_lower for word in ["hi", "hello", "hey", "good morning"]):
        return {
            "intent": "greeting",
            "next_node": "knowledge_engine",
            "reasoning": "Detected greeting pattern",
            "show_risks": bool(draft_risks),
            "confidence": 0.8
        }
    
    elif any(word in message_lower for word in ["approve", "accept"]) and "r-" in message_lower:
        return {
            "intent": "review_risks",
            "next_node": "risk_reviewer" if draft_risks else "knowledge_engine",
            "reasoning": "Detected risk approval pattern",
            "show_risks": bool(draft_risks),
            "confidence": 0.7
        }
    
    elif any(word in message_lower for word in ["change", "update", "edit"]) and draft_risks:
        return {
            "intent": "review_risks", 
            "next_node": "risk_reviewer",
            "reasoning": "Detected risk edit pattern",
            "show_risks": bool(draft_risks),
            "confidence": 0.7
        }
    
    elif any(word in message_lower for word in ["generate", "create"]) and "risk" in message_lower:
        return {
            "intent": "generate_risks",
            "next_node": "risk_generator", 
            "reasoning": "Detected risk generation pattern",
            "show_risks": False,
            "confidence": 0.8
        }
    
    elif any(word in message_lower for word in ["proceed to report", "generate report", "create report", "finish metadata"]):
        # Check if metadata is already completed - if so, go to report_generator
        # Check if we have approved risks with metadata (asset_value indicates metadata completion)
        if draft_risks and any(risk.get("is_approved", False) and risk.get("asset_value") is not None for risk in draft_risks):
            return {
                "intent": "report_generation",
                "next_node": "report_generator",
                "reasoning": "User wants to proceed to report generation - metadata already completed",
                "show_risks": bool(draft_risks),
                "confidence": 0.9
            }
        else:
            return {
                "intent": "metadata_collection",
                "next_node": "metadata_collector",
                "reasoning": "User wants to proceed but metadata not completed yet",
                "show_risks": bool(draft_risks),
                "confidence": 0.8
            }
    
    elif any(word in message_lower for word in ["save metadata", "done with metadata"]):
        # Always route to metadata_collector for explicit metadata save operations
        return {
            "intent": "metadata_collection",
            "next_node": "metadata_collector",
            "reasoning": "User explicitly saving metadata",
            "show_risks": bool(draft_risks),
            "confidence": 0.8
        }
    
    else:
        # Default fallback
        return {
            "intent": "other",
            "next_node": "knowledge_engine",
            "reasoning": "Fallback - no clear pattern detected",
            "show_risks": bool(draft_risks),
            "confidence": 0.5
        }