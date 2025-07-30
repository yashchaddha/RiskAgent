from typing import Dict, Any, Optional
from config.settings import settings
from openai import AsyncOpenAI

class LLMConfig:
    """Configuration for LLM (ChatGPT) integration"""
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.model = settings.openai_model
        self.temperature = settings.openai_temperature
        self.max_tokens = settings.openai_max_tokens
        
    def get_client(self) -> AsyncOpenAI:
        """Get OpenAI client instance"""
        if self.client is None:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self.client
    
    def get_default_params(self) -> Dict[str, Any]:
        """Get default parameters for LLM calls"""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
    
    def get_intent_classification_params(self) -> Dict[str, Any]:
        """Parameters optimized for intent classification"""
        return {
            "model": self.model,
            "temperature": 0.1,  # Lower temperature for consistent classification
            "max_tokens": 50     # Short responses for intent
        }
    
    def get_risk_generation_params(self) -> Dict[str, Any]:
        """Parameters optimized for risk generation"""
        return {
            "model": self.model,
            "temperature": 0.8,   # Higher creativity for risk generation
            "max_tokens": 1500    # Longer responses for detailed risks
        }
    
    def get_general_qa_params(self) -> Dict[str, Any]:
        """Parameters optimized for general Q&A"""
        return {
            "model": self.model,
            "temperature": 0.7,   # Balanced for informative responses
            "max_tokens": 800     # Medium length responses
        }
    
    def get_report_generation_params(self) -> Dict[str, Any]:
        """Parameters optimized for report generation"""
        return {
            "model": self.model,
            "temperature": 0.6,   # Structured and professional
            "max_tokens": 2000    # Long responses for detailed reports
        }

# LLM Model Configurations
LLM_MODEL_CONFIGS = {
    "gpt-4o": {
        "context_window": 8192,
        "cost_per_1k_tokens": {"input": 0.03, "output": 0.06},
        "best_for": ["complex_reasoning", "report_generation"]
    },
    "gpt-4-turbo": {
        "context_window": 128000,
        "cost_per_1k_tokens": {"input": 0.01, "output": 0.03},
        "best_for": ["long_context", "document_analysis"]
    },
    "gpt-3.5-turbo": {
        "context_window": 16385,
        "cost_per_1k_tokens": {"input": 0.0015, "output": 0.002},
        "best_for": ["quick_responses", "intent_classification"]
    }
}

# System Messages for Different Tasks
SYSTEM_MESSAGES = {
    "intent_classification": """You are an expert at understanding user intents in a risk management context. 
Classify the user's message into one of these intents:
- general_question: Questions about risks, definitions, explanations
- change_matrix: Requests to modify likelihood/impact matrix size
- generate_risks: Requests to create/generate new risks
- view_risks: Requests to see existing finalized risks
- finalize_risks: Ready to finalize selected risks
- fill_additional_data: Ready to fill additional risk data
- generate_report: Request to create final risk report
- approve_report: Approval for report generation
- reject_report: Rejection of report generation

Respond with only the intent name.""",

    "risk_generation": """You are an expert risk management consultant. Generate realistic, specific risks 
for organizations based on their industry and context. Each risk should be relevant, actionable, 
and include appropriate treatment strategies.""",

    "general_qa": """You are a helpful risk management expert assistant. Answer questions about risk management,
definitions, best practices, and methodologies. Be informative, clear, and professional.""",

    "welcome_message": """You are a friendly risk management assistant. Create personalized welcome messages
that acknowledge the user's progress and guide them on next steps in their risk assessment journey.""",

    "report_generation": """You are a professional risk management consultant creating executive-level risk reports.
Generate comprehensive, well-structured reports that provide clear insights and recommendations."""
}

# Global LLM configuration instance
llm_config = LLMConfig()