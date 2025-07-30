from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from graph.state.graph_state import RiskAgentState, set_error, clear_error
from config import llm_config, get_logger
from prompts import get_general_qa_prompt, prompt_manager
import time

logger = get_logger(__name__)

async def general_qa_node(state: RiskAgentState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    messages = state.get("messages", [])
    temp_data = state.get("temp_data", {})
    user_data = temp_data.get("user_data", {})
    current_stage = state.get("current_stage")
    
    logger.info(f"General Q&A node called for user: {user_id}, stage: {current_stage}")
    
    try:
        # Get last user message
        last_human_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human_message = msg.content
                break
        
        if not last_human_message:
            error_msg = "No user question found for Q&A"
            logger.error(error_msg)
            return set_error(state, error_msg)
        
        logger.info(f"Answering question: '{last_human_message[:100]}...'")
        
        # Build user context for personalized response
        user_context = {
            "organization": user_data.get("organization", "Not specified"),
            "industry": user_data.get("industry", "Not specified"),
            "current_stage": current_stage,
            "matrix_size": f"{len(user_data.get('likelihood_scale', []))}" + 
                          f"x{len(user_data.get('impact_scale', []))}",
            "finalized_risks_count": temp_data.get("progress_summary", {}).get("finalized_risks_count", 0),
            "generated_risks_count": temp_data.get("progress_summary", {}).get("generated_risks_count", 0)
        }
        
        # Get Q&A prompt with context
        prompt_data = get_general_qa_prompt(last_human_message, user_context)
        
        # Check for common topics that have pre-defined responses
        common_topics = ["risk_definition", "risk_matrix", "risk_treatment", 
                        "likelihood_assessment", "impact_assessment"]
        
        topic_response = None
        for topic in common_topics:
            if any(keyword in last_human_message.lower() 
                   for keyword in topic.split("_")):
                topic_response = None
                if topic_response:
                    logger.info(f"Using pre-defined response for topic: {topic}")
                    break
        
        if topic_response:
            # Use pre-defined response with context
            contextualized_response = f"{topic_response}\n\nFor {user_context['organization']} in the {user_context['industry']} sector, this is particularly relevant to your current risk assessment."
            logger.info(f"Contextualized response generated for topic: {topic}")
            return {
                **clear_error(state),
                "messages": messages + [
                    AIMessage(content=contextualized_response)
                ],
                "last_action": f"answered_predefined_topic_{topic}"
            }
        
        # Call LLM for personalized response
        client = llm_config.get_client()
        start_time = time.time()
        
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_data["system"]},
                {"role": "user", "content": prompt_data["user"]}
            ],
            **llm_config.get_general_qa_params()
        )
        
        response_time = (time.time() - start_time) * 1000
        answer = response.choices[0].message.content
        
        logger.info(f"Q&A response generated in {response_time:.2f}ms, tokens: {response.usage.total_tokens}")
        
        # Add helpful next steps based on current stage
        next_steps_guidance = get_stage_specific_next_steps(current_stage, user_context)
        if next_steps_guidance:
            answer += f"\n\n{next_steps_guidance}"
        
        return {
            **clear_error(state),
            "messages": messages + [
                AIMessage(content=answer)
            ],
            "last_action": "answered_general_question"
        }
        
    except Exception as e:
        error_msg = f"General Q&A error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Provide fallback response
        fallback_response = """I'm here to help with risk management questions. You can ask me about:

• Risk definitions and concepts
• How to assess likelihood and impact
• Risk treatment strategies
• Industry-specific risk considerations
• Best practices for risk management

What specific aspect of risk management would you like to know more about?"""
        
        return {
            **clear_error(state),
            "messages": messages + [
                AIMessage(content=fallback_response)
            ],
            "last_action": "general_qa_fallback_response"
        }

def get_stage_specific_next_steps(current_stage: str, user_context: dict) -> str:
    
    stage_guidance = {
        "welcome": """
**Next Steps:** Ready to start? Ask me to "generate risks" for your organization, or feel free to ask any questions about risk management concepts.""",
        
        "risk_generation": """
**Next Steps:** You can generate more risks, or if you're ready, let me know which risks you'd like to finalize.""",
        
        "risk_editing": """
**Next Steps:** Review your generated risks and let me know which ones you'd like to finalize, or ask for more risks if needed.""",
        
        "data_collection": """
**Next Steps:** Once you've filled in the additional risk details, we can generate your comprehensive risk report.""",
        
        "awaiting_report_approval": """
**Next Steps:** When you're ready, I can generate your final risk management report with all your assessed risks.""",
        
        "report_ready": """
**Next Steps:** Your risk assessment is complete! You can view your report, start a new assessment, or ask questions about ongoing risk management."""
    }
    
    base_guidance = stage_guidance.get(current_stage, "")
    
    # Add progress context if available
    finalized_count = user_context.get("finalized_risks_count", 0)
    if finalized_count > 0:
        base_guidance += f"\n\n*Current Progress: {finalized_count} risks finalized*"
    
    return base_guidance

async def help_node(state: RiskAgentState) -> Dict[str, Any]:
    
    user_id = state.get("user_id")
    current_stage = state.get("current_stage")
    temp_data = state.get("temp_data", {})
    user_data = temp_data.get("user_data", {})
    
    logger.info(f"Help node called for user: {user_id}, stage: {current_stage}")
    
    help_content = {
        "welcome": f"""
**Welcome to the Risk Management Agent!**

I'm here to help {user_data.get('organization', 'your organization')} identify and assess risks. Here's what we can do together:

**🎯 What I Can Help With:**
• Generate specific risks for your industry
• Assess likelihood and impact using risk matrices
• Develop treatment strategies for each risk
• Create comprehensive risk reports

**🚀 Getting Started:**
• Ask me to "generate risks" to begin your assessment
• You can change your risk matrix size (3x3, 4x4, 5x5) anytime
• Feel free to ask questions about risk management concepts

**💬 Example Questions:**
• "Generate risks for my organization"
• "What is operational risk?"
• "Change to 4x4 matrix"
• "Explain risk treatment strategies"

Ready to start your risk assessment journey?
""",
        
        "risk_generation": """
**Risk Generation Help**

I've generated risks specific to your organization and industry. Here's what you can do:

**✅ Available Actions:**
• Review the generated risks in the popup table
• Select which risks are most relevant
• Edit risk descriptions or assessments
• Generate additional risks if needed
• Finalize your selected risks

**🔄 Commands You Can Use:**
• "Generate more risks" - Get additional risk suggestions
• "Finalize these risks" - Move selected risks forward
• "Change matrix to 4x4" - Adjust assessment granularity

The goal is to build a comprehensive list of risks that are specific and actionable for your organization.
""",
        
        "risk_editing": """
**Risk Editing Help**

You're currently selecting and refining your generated risks.

**✏️ What You Can Do:**
• Select risks that are most relevant to your organization
• Edit risk descriptions to be more specific
• Adjust likelihood and impact assessments
• Modify treatment strategies and measures
• Generate additional risks if you need more options

**➡️ Next Steps:**
Once you're satisfied with your risk selection, finalize them to move to detailed data collection.

Need more risks or ready to proceed?
""",
        
        "data_collection": """
**Data Collection Help**

Great! You've finalized your key risks. Now let's add detailed information:

**📋 Additional Information Needed:**
• Asset Value - Financial impact if risk occurs
• Department - Which department owns this risk
• Risk Owner - Person responsible for managing the risk
• Target Date - When mitigation should be completed
• Risk Progress - Current status of risk treatment
• Residual Exposure - Remaining risk after treatment

**🎯 Purpose:**
This information creates a complete risk register that your organization can use for ongoing risk management.

Ready to fill in these details?
""",
        
        "awaiting_report_approval": """
**Report Generation Help**

Excellent progress! You've completed your risk assessment and we're ready to generate your final report.

**📊 Your Report Will Include:**
• Executive summary of your risk landscape
• Detailed analysis of all assessed risks
• Treatment recommendations and priorities
• Implementation roadmap
• Complete risk register

**✅ Final Step:**
Just confirm that you're ready for me to generate your comprehensive risk management report.

Should I proceed with generating your risk report?
""",
        
        "report_ready": """
**Assessment Complete!**

Congratulations! You've completed your risk assessment.

**📈 What You've Accomplished:**
• Identified key risks for your organization
• Assessed likelihood and impact
• Developed treatment strategies
• Created a comprehensive risk register
• Generated an executive risk report

**🔄 What's Next:**
• Implement your risk treatment plans
• Regular monitoring and review
• Update assessments as business changes
• Consider periodic re-assessments

**💡 Ongoing Support:**
You can always ask me questions about risk management, generate new risks, or start a fresh assessment.
"""
    }
    
    help_message = help_content.get(current_stage, help_content["welcome"])
    
    return {
        **clear_error(state),
        "messages": state.get("messages", []) + [
            AIMessage(content=help_message)
        ],
        "last_action": f"provided_help_for_stage_{current_stage}"
    }