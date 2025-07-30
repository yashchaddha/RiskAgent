from typing import Dict, List, Any, Optional
from prompts.prompts import (
    INTENT_CLASSIFICATION_SYSTEM_PROMPT,
    get_intent_classification_prompt,
    validate_intent_classification,
    INTENT_PATTERNS,
    WELCOME_MESSAGE_SYSTEM_PROMPT,
    get_welcome_prompt_new_user,
    get_welcome_prompt_returning_user,
    get_quick_welcome_message,
    WELCOME_TEMPLATES,
    RISK_GENERATION_SYSTEM_PROMPT,
    get_risk_generation_prompt,
    get_additional_risk_generation_prompt,
    validate_generated_risk,
    get_industry_risk_guidance,
    GENERAL_QA_SYSTEM_PROMPT,
    get_general_qa_prompt,
    get_stage_specific_guidance,
    COMMON_QA_TOPICS,
    MATRIX_UPDATE_SYSTEM_PROMPT,
    REPORT_GENERATION_SYSTEM_PROMPT,
    get_matrix_update_prompt,
    get_matrix_explanation_prompt,
    get_report_generation_prompt,
)

class PromptManager:
    """Centralized prompt management for the Risk Management Agent"""
    
    def __init__(self):
        self.system_prompts = {
            "intent_classification": INTENT_CLASSIFICATION_SYSTEM_PROMPT,
            "welcome_message": WELCOME_MESSAGE_SYSTEM_PROMPT,
            "risk_generation": RISK_GENERATION_SYSTEM_PROMPT,
            "general_qa": GENERAL_QA_SYSTEM_PROMPT,
            "matrix_update": MATRIX_UPDATE_SYSTEM_PROMPT,
            "report_generation": REPORT_GENERATION_SYSTEM_PROMPT,
        }
    
    def get_system_prompt(self, prompt_type: str) -> str:
        """Get system prompt for specific task type"""
        return self.system_prompts.get(prompt_type, self.system_prompts["general_qa"])
    
    # Intent Classification Methods
    def get_intent_prompt(self, user_message: str, current_stage: str, 
                         conversation_context: str = "") -> Dict[str, str]:
        """Get intent classification prompt and system message"""
        return {
            "system": self.get_system_prompt("intent_classification"),
            "user": get_intent_classification_prompt(user_message, current_stage, conversation_context)
        }
    
    def validate_intent(self, user_message: str, predicted_intent: str) -> bool:
        """Validate predicted intent against message patterns"""
        return validate_intent_classification(user_message, predicted_intent)
    
    # Welcome Message Methods
    def get_welcome_prompt_new(self, user_name: str, organization: str, industry: str) -> Dict[str, str]:
        """Get welcome prompt for new users"""
        from .prompts import get_welcome_prompt_new_user as get_template
        return {
            "system": self.get_system_prompt("welcome_message"),
            "user": get_template(user_name, organization, industry)
        }
    
    def get_welcome_prompt_returning(self, user_name: str, organization: str, 
                                   current_stage: str, progress_summary: dict) -> Dict[str, str]:
        """Get welcome prompt for returning users"""
        from .prompts import get_welcome_prompt_returning_user as get_template
        return {
            "system": self.get_system_prompt("welcome_message"),
            "user": get_template(user_name, organization, current_stage, progress_summary)
        }
    
    def get_quick_welcome(self, template_type: str, **kwargs) -> str:
        """Get pre-formatted welcome message"""
        return get_quick_welcome_message(template_type, **kwargs)
    
    # Risk Generation Methods
    def get_risk_generation_prompt(self, organization: str, industry: str, 
                                 likelihood_scale: List[str], impact_scale: List[str],
                                 additional_context: str = "") -> Dict[str, str]:
        """Get risk generation prompt"""
        user_prompt = f"""Organization: {organization}
Industry: {industry}
Likelihood Scale: {', '.join(likelihood_scale)} (from lowest to highest)
Impact Scale: {', '.join(impact_scale)} (from lowest to highest)

{additional_context}

Please generate 5-8 specific risks for this organization, including likelihood and impact assessments using the provided scales."""
        
        return {
            "system": self.get_system_prompt("risk_generation"),
            "user": user_prompt
        }
    
    def get_additional_risks_prompt(self, organization: str, industry: str,
                                  likelihood_scale: List[str], impact_scale: List[str],
                                  existing_risks_count: int) -> Dict[str, str]:
        """Get prompt for generating additional risks"""
        return {
            "system": self.get_system_prompt("risk_generation"),
            "user": get_additional_risk_generation_prompt(organization, industry, likelihood_scale,
                                                        impact_scale, existing_risks_count)
        }
    
    def validate_risk(self, risk_data: dict, allowed_impact: List[str], 
                     allowed_likelihood: List[str]) -> bool:
        """Validate generated risk data"""
        return validate_generated_risk(risk_data, allowed_impact, allowed_likelihood)
    
    # General Q&A Methods
    def get_qa_prompt(self, user_question: str, user_context: dict) -> Dict[str, str]:
        """Get general Q&A prompt with context"""
        user_prompt = f"""User Question: {user_question}

User Context:
- Organization: {user_context.get('organization', 'Not specified')}
- Industry: {user_context.get('industry', 'Not specified')}
- Current Stage: {user_context.get('current_stage', 'welcome')}
- Matrix Size: {user_context.get('matrix_size', '3x3')}
- Finalized Risks: {user_context.get('finalized_risks_count', 0)}
- Generated Risks: {user_context.get('generated_risks_count', 0)}

Please provide a helpful, contextual response about risk management."""
        
        return {
            "system": self.get_system_prompt("general_qa"),
            "user": user_prompt
        }
    
    def get_topic_response(self, topic: str, user_context: dict) -> str:
        """Get pre-defined response for common topics"""
        return COMMON_QA_TOPICS.get(topic, "")
    
    # Matrix Update Methods
    def get_matrix_update_prompt(self, current_matrix: str, requested_matrix: str,
                               current_scales: dict, new_scales: dict) -> Dict[str, str]:
        """Get matrix update confirmation prompt"""
        return {
            "system": self.get_system_prompt("matrix_update"),
            "user": get_matrix_update_prompt(current_matrix, requested_matrix, 
                                           current_scales, new_scales)
        }
    
    def get_matrix_explanation(self, matrix_size: str) -> str:
        """Get explanation of specific matrix size"""
        return get_matrix_explanation_prompt(matrix_size)
    
    # Report Generation Methods
    def get_report_prompt(self, user_data: dict, finalized_risks: List[dict]) -> Dict[str, str]:
        """Get comprehensive report generation prompt"""
        return {
            "system": self.get_system_prompt("report_generation"),
            "user": get_report_generation_prompt(user_data, finalized_risks)
        }
    
    # Utility Methods
    def get_industry_guidance(self, industry: str) -> str:
        """Get industry-specific risk guidance"""
        return get_industry_risk_guidance(industry)
    
    def get_stage_guidance(self, stage: str) -> str:
        """Get stage-specific guidance"""
        return get_stage_specific_guidance(stage)
    
    def get_available_intents(self) -> List[str]:
        """Get list of available user intents"""
        return list(INTENT_PATTERNS.keys())
    
    def format_conversation_context(self, messages: List[dict], max_messages: int = 5) -> str:
        """Format recent conversation for context"""
        if not messages:
            return ""
        
        recent_messages = messages[-max_messages:]
        context_parts = []
        
        for msg in recent_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if len(content) > 100:
                content = content[:97] + "..."
            context_parts.append(f"{role}: {content}")
        
        return " | ".join(context_parts)

# Global prompt manager instance
prompt_manager = PromptManager()

# Convenience functions for easy access
# Convenience wrapper functions that call the actual prompt templates
def get_intent_prompt(user_message: str, current_stage: str, conversation_context: str = "") -> Dict[str, str]:
    """Get intent classification prompt"""
    return prompt_manager.get_intent_prompt(user_message, current_stage, conversation_context)

def get_welcome_prompt_new_user(user_name: str, organization: str, industry: str) -> Dict[str, str]:
    """Get welcome prompt for new users"""
    from .prompts import get_welcome_prompt_new_user as template_fn
    return {
        "system": prompt_manager.get_system_prompt("welcome_message"),
        "user": template_fn(user_name, organization, industry)
    }

def get_welcome_prompt_returning_user(user_name: str, organization: str, current_stage: str, progress_summary: dict) -> Dict[str, str]:
    """Get welcome prompt for returning users"""
    from .prompts import get_welcome_prompt_returning_user as template_fn
    return {
        "system": prompt_manager.get_system_prompt("welcome_message"),
        "user": template_fn(user_name, organization, current_stage, progress_summary)
    }

def get_risk_generation_prompt(organization: str, industry: str, likelihood_scale: List[str], impact_scale: List[str], additional_context: str = "") -> Dict[str, str]:
    """Get risk generation prompt"""
    return prompt_manager.get_risk_generation_prompt(organization, industry, likelihood_scale, impact_scale, additional_context)

def get_general_qa_prompt(user_question: str, user_context: dict) -> Dict[str, str]:
    """Get general Q&A prompt"""
    return prompt_manager.get_qa_prompt(user_question, user_context)

def get_report_generation_prompt(user_data: dict, finalized_risks: List[dict]) -> Dict[str, str]:
    """Get report generation prompt"""
    from .prompts import get_report_generation_prompt as template_fn
    return {
        "system": prompt_manager.get_system_prompt("report_generation"),
        "user": template_fn(user_data, finalized_risks)
    }

# Export main components
__all__ = [
    "prompt_manager",
    "PromptManager",
    "get_intent_prompt",
    "get_welcome_prompt_new_user", 
    "get_welcome_prompt_returning_user",
    "get_risk_generation_prompt",
    "get_general_qa_prompt",
    "get_report_generation_prompt"
]