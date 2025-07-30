from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from graph.state.graph_state import (RiskAgentState, update_stage, set_popup, set_awaiting_input, set_error, clear_error, update_temp_data)
from database.repository import repo_factory
from models.models import UserStage, RiskReport
from config import llm_config, get_logger, MATRIX_CONFIGS, get_matrix_scales
from prompts import prompt_manager, get_report_generation_prompt
import json
import time
from datetime import datetime

logger = get_logger(__name__)

async def matrix_update_node(state: RiskAgentState) -> Dict[str, Any]:    
    user_id = state.get("user_id")
    messages = state.get("messages", [])
    temp_data = state.get("temp_data", {})
    user_data = temp_data.get("user_data", {})
    
    logger.info(f"Matrix update node called for user: {user_id}")
    
    try:
        # Extract matrix size from user message
        last_human_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human_message = msg.content.lower()
                break
        
        if not last_human_message:
            error_msg = "No user message found for matrix update"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        # Detect requested matrix size
        requested_matrix = None
        if any(size in last_human_message for size in ["3x3", "3 x 3", "3*3", "3 * 3"]):
            requested_matrix = "3x3"
        elif any(size in last_human_message for size in ["4x4", "4 x 4", "4*4", "4 * 4"]):
            requested_matrix = "4x4" 
        elif any(size in last_human_message for size in ["5x5", "5 x 5", "5*5", "5 * 5"]):
            requested_matrix = "5x5"
        
        if not requested_matrix:
            # Ask for clarification
            response = """I can help you change your risk matrix size. Which matrix would you like to use?

**Available Options:**
• **3x3 Matrix**: Simple (Low, Medium, High) - Good for quick assessments
• **4x4 Matrix**: Moderate detail (Very Low, Low, Medium, High) 
• **5x5 Matrix**: High detail (Very Low, Low, Medium, High, Very High) - Most precise

Just tell me "change to 4x4" or whichever size you prefer!"""
            
            return {
                **clear_error(state),
                "messages": messages + [AIMessage(content=response)],
                "last_action": "matrix_clarification_requested"
            }
        
        # Get current and new matrix configurations
        current_likelihood = user_data.get("likelihood_scale", ["Low", "Medium", "High"])
        current_impact = user_data.get("impact_scale", ["Low", "Medium", "High"])
        current_matrix = f"{len(current_likelihood)}x{len(current_impact)}"
        
        new_scales = get_matrix_scales(requested_matrix)
        new_likelihood = new_scales["likelihood_scale"]
        new_impact = new_scales["impact_scale"]
        
        logger.info(f"Updating matrix from {current_matrix} to {requested_matrix}")
        
        # Update database
        user_repo = repo_factory.user_repository
        success = await user_repo.update_risk_scales(user_id, new_likelihood, new_impact)
        
        if not success:
            error_msg = "Failed to update matrix in database"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        # Generate confirmation response
        client = llm_config.get_client()
        
        current_scales = {"likelihood_scale": current_likelihood, "impact_scale": current_impact}
        new_scales_dict = {"likelihood_scale": new_likelihood, "impact_scale": new_impact}
        
        prompt_data = prompt_manager.get_matrix_update_prompt(
            current_matrix, requested_matrix, current_scales, new_scales_dict
        )
        
        start_time = time.time()
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_data["system"]},
                {"role": "user", "content": prompt_data["user"]}
            ],
            **llm_config.get_general_qa_params()
        )
        
        response_time = (time.time() - start_time) * 1000
        confirmation_message = response.choices[0].message.content
        
        logger.info(f"Matrix updated successfully to {requested_matrix} in {response_time:.2f}ms")
        
        # Update user data in temp storage
        updated_user_data = user_data.copy()
        updated_user_data["likelihood_scale"] = new_likelihood
        updated_user_data["impact_scale"] = new_impact
        
        return {
            **clear_error(state),
            **update_temp_data(state, {"user_data": updated_user_data}),
            "messages": messages + [AIMessage(content=confirmation_message)],
            "last_action": f"matrix_updated_to_{requested_matrix}"
        }
        
    except Exception as e:
        error_msg = f"Matrix update error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            **set_error(state, error_msg),
            "messages": messages + [
                AIMessage(content="I encountered an error updating your matrix. Please try again.")
            ]
        }

async def risk_finalization_node(state: RiskAgentState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    temp_data = state.get("temp_data", {})
    
    logger.info(f"Risk finalization node called for user: {user_id}")
    
    try:
        # Get selected risks from temp_data (set by API endpoint)
        selected_risk_ids = temp_data.get("selected_risk_ids", [])
        edited_risks = temp_data.get("edited_risks", [])
        
        if not selected_risk_ids:
            error_msg = "No risks selected for finalization"
            logger.warning(error_msg)
            return {
                **set_error(state, error_msg),
                "messages": state.get("messages", []) + [
                    AIMessage(content="Please select at least one risk to finalize.")
                ]
            }
        
        logger.info(f"Finalizing {len(selected_risk_ids)} risks")
        
        # Apply any edits to generated risks first
        risk_repo = repo_factory.risk_repository
        for edited_risk in edited_risks:
            risk_id = edited_risk.get("risk_id")
            if risk_id and risk_id in selected_risk_ids:
                # Update the generated risk with edits
                update_data = {
                    "description": edited_risk.get("description"),
                    "impact": edited_risk.get("impact"),
                    "likelihood": edited_risk.get("likelihood"),
                    "treatment_strategy": edited_risk.get("treatment_strategy"),
                    "treatment_measures": edited_risk.get("treatment_measures")
                }
                await risk_repo.update_generated_risk(risk_id, update_data)
                logger.info(f"Updated risk {risk_id} with edits")
        
        # Finalize selected risks
        logger.info(f"Attempting to finalize {len(selected_risk_ids)} risks for user {user_id}")
        finalized_ids = await risk_repo.finalize_risks(selected_risk_ids, user_id)
        
        # Log the exact finalization result
        logger.info(f"Finalization result: received {len(finalized_ids)} IDs out of {len(selected_risk_ids)} requested")
        
        if not finalized_ids:
            error_msg = "Failed to finalize risks"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        logger.info(f"Successfully finalized {len(finalized_ids)} risks")
        
        # Get total finalized count for user
        total_finalized = await risk_repo.get_finalized_risks_count(user_id)
        
        response_message = f"""Perfect! I've finalized {len(finalized_ids)} risks for your organization.

**Next Step:** We need to collect some additional details for each risk to create your comprehensive risk register:
• Asset Value - Potential financial impact
• Department - Which department manages this risk
• Risk Owner - Person responsible for the risk
• Target Date - When to complete mitigation
• Progress Status - Current implementation status
• Residual Exposure - Remaining risk after treatment

Would you like to fill in these additional details now?"""

        return {
            **clear_error(state),
            **update_stage(state, UserStage.DATA_COLLECTION),
            "messages": state.get("messages", []) + [
                AIMessage(content=response_message)
            ],
            "temp_data": {
                **temp_data,
                "finalized_risk_ids": finalized_ids,
                "total_finalized_count": total_finalized,
                "selected_risk_ids": None,  # Clear selection
                "edited_risks": None
            },
            "last_action": f"finalized_{len(finalized_ids)}_risks"
        }
        
    except Exception as e:
        error_msg = f"Risk finalization error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # More detailed logging for debugging
        logger.error(f"Risk finalization details - user_id: {user_id}")
        logger.error(f"Selected risk IDs: {selected_risk_ids}")
        
        if edited_risks:
            for i, risk in enumerate(edited_risks):
                logger.error(f"Edited risk {i+1}: {risk}")
        
        return {
            **set_error(state, error_msg),
            "messages": state.get("messages", []) + [
                AIMessage(content="I encountered an error finalizing your risks. Please try again.")
            ]
        }

async def data_collection_node(state: RiskAgentState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    temp_data = state.get("temp_data", {})
    
    logger.info(f"Data collection node called for user: {user_id}")
    
    try:
        # Get finalized risks for data collection popup
        risk_repo = repo_factory.risk_repository
        finalized_risks = await risk_repo.get_finalized_risks_by_user(user_id)
        
        if not finalized_risks:
            error_msg = "No finalized risks found for data collection"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        # Check if this is a request to show popup or process submitted data
        additional_data = temp_data.get("additional_data")
        
        if additional_data:
            # Process submitted additional data
            logger.info(f"Processing additional data for {len(additional_data)} risks")
            
            for risk_data in additional_data:
                risk_id = risk_data.get("risk_id")
                if risk_id:
                    update_data = {
                        "asset_value": risk_data.get("asset_value"),
                        "department": risk_data.get("department"),
                        "risk_owner": risk_data.get("risk_owner"),
                        "target_date": risk_data.get("target_date"),
                        "risk_progress": risk_data.get("risk_progress"),
                        "residual_exposure": risk_data.get("residual_exposure")
                    }
                    success = await risk_repo.update_finalized_risk_additional_data(risk_id, update_data)
                    if success:
                        logger.info(f"Updated additional data for risk {risk_id}")
            
            # Move to report approval stage
            response_message = """Excellent! All additional risk information has been collected. 

Your comprehensive risk assessment is now complete with:
✅ Identified and assessed risks
✅ Treatment strategies and measures  
✅ Detailed risk information and ownership
✅ Implementation timelines and progress tracking

**Ready for Your Risk Report?**
I can now generate your comprehensive risk management report that includes an executive summary, detailed analysis, and actionable recommendations.

Should I proceed with generating your final risk report?"""
            
            return {
                **clear_error(state),
                **update_stage(state, UserStage.AWAITING_REPORT_APPROVAL),
                **set_awaiting_input(state, True),
                "messages": state.get("messages", []) + [
                    AIMessage(content=response_message)
                ],
                "temp_data": {
                    **temp_data,
                    "additional_data": None,  # Clear processed data
                    "data_collection_complete": True
                },
                "last_action": "additional_data_collected"
            }
        
        else:
            # Show data collection popup
            popup_data = {
                "type": "data_collection",
                "risks": [
                    {
                        "risk_id": risk.risk_id,
                        "description": risk.description,
                        "current_data": {
                            "asset_value": risk.asset_value,
                            "department": risk.department,
                            "risk_owner": risk.risk_owner,
                            "target_date": risk.target_date.isoformat() if risk.target_date else None,
                            "risk_progress": risk.risk_progress,
                            "residual_exposure": risk.residual_exposure
                        }
                    }
                    for risk in finalized_risks
                ]
            }
            
            response_message = f"I've prepared a form for you to add detailed information to your {len(finalized_risks)} finalized risks. Please fill in the additional details in the popup."
            
            return {
                **clear_error(state),
                **set_popup(state, "data_collection_popup", popup_data),
                "messages": state.get("messages", []) + [
                    AIMessage(content=response_message)
                ],
                "last_action": "data_collection_popup_shown"
            }
        
    except Exception as e:
        error_msg = f"Data collection error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            **set_error(state, error_msg),
            "messages": state.get("messages", []) + [
                AIMessage(content="I encountered an error with data collection. Please try again.")
            ]
        }


async def report_generation_node(state: RiskAgentState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    temp_data = state.get("temp_data", {})
    user_data = temp_data.get("user_data", {})
    
    logger.info(f"Report generation node called for user: {user_id}")
    
    try:
        # Get finalized risks with all data
        risk_repo = repo_factory.risk_repository
        finalized_risks = await risk_repo.get_finalized_risks_by_user(user_id)
        
        if not finalized_risks:
            error_msg = "No finalized risks found for report generation"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        # Prepare risks data for report
        risks_data = [
            {
                "description": risk.description,
                "impact": risk.impact,
                "likelihood": risk.likelihood,
                "treatment_strategy": risk.treatment_strategy,
                "treatment_measures": risk.treatment_measures,
                "asset_value": risk.asset_value,
                "department": risk.department,
                "risk_owner": risk.risk_owner,
                "target_date": risk.target_date,
                "risk_progress": risk.risk_progress,
                "residual_exposure": risk.residual_exposure
            }
            for risk in finalized_risks
        ]
        
        # Add assessment date and matrix info
        report_user_data = user_data.copy()
        report_user_data["assessment_date"] = datetime.utcnow().strftime("%B %Y")
        report_user_data["matrix_size"] = f"{len(user_data.get('likelihood_scale', []))}x{len(user_data.get('impact_scale', []))}"
        
        # Generate report using LLM
        prompt_data = get_report_generation_prompt(report_user_data, risks_data)
        
        client = llm_config.get_client()
        start_time = time.time()
        
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_data["system"]},
                {"role": "user", "content": prompt_data["user"]}
            ],
            **llm_config.get_report_generation_params()
        )
        
        response_time = (time.time() - start_time) * 1000
        report_content = response.choices[0].message.content
        
        logger.info(f"Risk report generated in {response_time:.2f}ms, tokens: {response.usage.total_tokens}")
        
        # Create report record
        risk_report = RiskReport(
            user_id=user_id,
            organization=user_data["organization"],
            industry=user_data["industry"],
            total_risks=len(finalized_risks),
            high_priority_risks=sum(1 for r in finalized_risks 
                                  if r.likelihood in user_data["likelihood_scale"][-2:] 
                                  and r.impact in user_data["impact_scale"][-2:]),
            report_content=report_content
        )
        
        # Save report to database
        report_repo = repo_factory.report_repository
        report_id = await report_repo.create_report(risk_report)
        
        logger.info(f"Risk report saved with ID: {report_id}")
        
        # Success message with PDF download option
        success_message = f"""🎉 **Your Risk Management Report is Ready!**

I've generated a comprehensive risk report for {user_data['organization']} that includes:

✅ **Executive Summary** - Key insights and strategic overview
✅ **Risk Analysis** - Detailed assessment of all {len(finalized_risks)} risks  
✅ **Treatment Recommendations** - Prioritized action plan
✅ **Implementation Roadmap** - Timeline and next steps
✅ **Risk Register** - Complete documentation for ongoing management

Your report is now available and has been saved to your account. You can download it as a PDF for professional presentation and sharing.

**What's Next?**
• Download your PDF report for implementation
• Implement the recommended treatment strategies
• Assign risk owners and set target dates
• Monitor progress regularly
• Update your risk assessment as your business evolves

Congratulations on completing your risk assessment! 🎯"""
        
        return {
            **clear_error(state),
            **update_stage(state, UserStage.REPORT_READY),
            "messages": state.get("messages", []) + [
                AIMessage(content=success_message)
            ],
            "temp_data": {
                **temp_data,
                "report_id": report_id,
                "report_content": report_content,
                "report_generated": True
            },
            "last_action": f"report_generated_{report_id}"
        }
        
    except Exception as e:
        error_msg = f"Report generation error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            **set_error(state, error_msg),
            "messages": state.get("messages", []) + [
                AIMessage(content="I encountered an error generating your report. Please try again.")
            ]
        }