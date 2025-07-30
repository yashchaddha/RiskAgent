from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
from graph.state.graph_state import RiskAgentState, update_stage, set_popup, set_error, clear_error, update_temp_data
from database.repository import repo_factory
from models.models import GeneratedRisk, UserStage
from config import llm_config, get_logger, POPUP_TYPES
from prompts import get_risk_generation_prompt, prompt_manager
import json
import time

logger = get_logger(__name__)

async def risk_generation_node(state: RiskAgentState) -> Dict[str, Any]:
    """
    Generate risks for user's organization and industry
    """
    
    user_id = state.get("user_id")
    temp_data = state.get("temp_data", {})
    user_data = temp_data.get("user_data", {})
    
    logger.info(f"Risk generation node called for user: {user_id}")
    
    try:
        if not user_data:
            error_msg = "No user data available for risk generation"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        organization = user_data.get("organization")
        industry = user_data.get("industry")
        likelihood_scale = user_data.get("likelihood_scale", ["Low", "Medium", "High"])
        impact_scale = user_data.get("impact_scale", ["Low", "Medium", "High"])
        
        logger.info(f"Generating risks for {organization} in {industry} industry")
        
        # Check if this is additional risk generation
        risk_repo = repo_factory.risk_repository
        existing_risks = await risk_repo.get_generated_risks_by_user(user_id)
        is_additional = len(existing_risks) > 0
        
        # Get appropriate prompt
        if is_additional:
            prompt_data = prompt_manager.get_additional_risks_prompt(
                organization, industry, likelihood_scale, impact_scale, len(existing_risks)
            )
            logger.info(f"Generating additional risks (existing: {len(existing_risks)})")
        else:
            prompt_data = get_risk_generation_prompt(
                organization, industry, likelihood_scale, impact_scale
            )
            logger.info("Generating initial risk set")
        
        # Call LLM for risk generation
        client = llm_config.get_client()
        start_time = time.time()
        
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_data["system"]},
                {"role": "user", "content": prompt_data["user"]}
            ],
            **llm_config.get_risk_generation_params()
        )
        
        response_time = (time.time() - start_time) * 1000
        risks_json = response.choices[0].message.content
        
        logger.info(f"LLM response received in {response_time:.2f}ms, tokens: {response.usage.total_tokens}")
        logger.info(f"Raw LLM response (first 500 chars): {risks_json[:500]}")
        
        # Parse and validate generated risks
        try:
            # Try to extract JSON from response if it's wrapped in markdown or text
            json_start = risks_json.find('[')
            json_end = risks_json.rfind(']') + 1
            
            if json_start != -1 and json_end != -1:
                risks_json_clean = risks_json[json_start:json_end]
                logger.info(f"Extracted JSON: {risks_json_clean[:200]}...")
            else:
                risks_json_clean = risks_json
            
            risks_data = json.loads(risks_json_clean)
            if not isinstance(risks_data, list):
                raise ValueError("Response is not a list of risks")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse risk JSON: {e}")
            logger.error(f"Attempted to parse: {risks_json_clean[:200] if 'risks_json_clean' in locals() else risks_json[:200]}")
            return {
                **set_error(state, "Failed to parse generated risks"),
                "messages": state.get("messages", []) + [
                    AIMessage(content="I encountered an error generating risks. Let me try again.")
                ]
            }
        
        # Validate and create risk objects
        valid_risks = []
        for i, risk_data in enumerate(risks_data):
            try:
                # Validate risk structure
                if not prompt_manager.validate_risk(risk_data, impact_scale, likelihood_scale):
                    logger.warning(f"Risk {i+1} failed validation, skipping")
                    continue
                
                # Create GeneratedRisk object
                generated_risk = GeneratedRisk(
                    user_id=user_id,
                    description=risk_data["description"],
                    impact=risk_data["impact"],
                    likelihood=risk_data["likelihood"],
                    treatment_strategy=risk_data["treatment_strategy"],
                    treatment_measures=risk_data["treatment_measures"]
                )
                valid_risks.append(generated_risk)
                
            except Exception as e:
                logger.warning(f"Error processing risk {i+1}: {e}")
                continue
        
        if not valid_risks:
            error_msg = "No valid risks generated"
            logger.error(error_msg)
            return {
                **set_error(state, error_msg),
                "messages": state.get("messages", []) + [
                    AIMessage(content="I had trouble generating risks. Let me try again with a different approach.")
                ]
            }
        
        logger.info(f"Generated {len(valid_risks)} valid risks")
        
        # Save risks to database
        try:
            risk_ids = await risk_repo.save_generated_risks(valid_risks)
            logger.info(f"Saved {len(risk_ids)} risks to database")
        except Exception as e:
            error_msg = f"Failed to save risks to database: {e}"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        # Prepare popup data for frontend
        popup_data = {
            "type": "risk_selection",
            "risks": [
                {
                    "risk_id": risk_ids[i],
                    "description": risk.description,
                    "impact": risk.impact,
                    "likelihood": risk.likelihood,
                    "treatment_strategy": risk.treatment_strategy,
                    "treatment_measures": risk.treatment_measures,
                    "selected": False  # Default unselected
                }
                for i, risk in enumerate(valid_risks)
            ],
            "total_generated": len(valid_risks),
            "is_additional": is_additional,
            "existing_count": len(existing_risks)
        }
        
        # Create response message
        if is_additional:
            response_message = f"I've generated {len(valid_risks)} additional risks for {organization}. Review them in the popup and select which ones you'd like to finalize."
        else:
            response_message = f"I've generated {len(valid_risks)} specific risks for {organization} in the {industry} industry. Please review them and select which ones are most relevant for your organization."
        
        # Update state
        return {
            **clear_error(state),
            **update_stage(state, UserStage.RISK_EDITING),
            **set_popup(state, POPUP_TYPES["RISK_SELECTION"], popup_data),
            **update_temp_data(state, {
                "generated_risk_ids": risk_ids,
                "total_risks_generated": len(valid_risks)
            }),
            "messages": state.get("messages", []) + [
                AIMessage(content=response_message)
            ],
            "last_action": f"risks_generated_{len(valid_risks)}_risks"
        }
        
    except Exception as e:
        error_msg = f"Risk generation error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            **set_error(state, error_msg),
            "messages": state.get("messages", []) + [
                AIMessage(content="I encountered an error while generating risks. Please try again.")
            ]
        }

async def view_risks_node(state: RiskAgentState) -> Dict[str, Any]:
    """
    Display user's finalized risks
    """
    
    user_id = state.get("user_id")
    logger.info(f"View risks node called for user: {user_id}")
    
    try:
        risk_repo = repo_factory.risk_repository
        
        # Get finalized risks
        finalized_risks = await risk_repo.get_finalized_risks_by_user(user_id)
        
        if not finalized_risks:
            response_message = """You don't have any finalized risks yet. 
            
Would you like me to generate some risks for your organization? Just ask me to "generate risks" and I'll create specific risks based on your industry and organization."""
        else:
            # Format risks for display
            risk_summaries = []
            for i, risk in enumerate(finalized_risks, 1):
                summary = f"""**Risk {i}: {risk.description[:100]}{'...' if len(risk.description) > 100 else ''}**
- Impact: {risk.impact} | Likelihood: {risk.likelihood}
- Strategy: {risk.treatment_strategy}
- Department: {risk.department or 'Not specified'}
- Owner: {risk.risk_owner or 'Not assigned'}"""
                risk_summaries.append(summary)
            
            response_message = f"""Here are your {len(finalized_risks)} finalized risks:

{chr(10).join(risk_summaries)}

You can generate more risks, modify existing ones, or proceed to generate your risk report."""
        
        logger.info(f"Displayed {len(finalized_risks)} finalized risks")
        
        return {
            **clear_error(state),
            "messages": state.get("messages", []) + [
                AIMessage(content=response_message)
            ],
            "last_action": f"displayed_{len(finalized_risks)}_finalized_risks"
        }
        
    except Exception as e:
        error_msg = f"View risks error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            **set_error(state, error_msg),
            "messages": state.get("messages", []) + [
                AIMessage(content="I encountered an error retrieving your risks. Please try again.")
            ]
        }