from prompts.main import (
    prompt_manager,
    PromptManager,
    get_intent_prompt,
    get_welcome_prompt_new_user,
    get_welcome_prompt_returning_user, 
    get_risk_generation_prompt,
    get_general_qa_prompt,
    get_report_generation_prompt,
)

# Export all main functions for easy import
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