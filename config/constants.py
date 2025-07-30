from typing import Dict, List

# Risk Matrix Configurations
MATRIX_CONFIGS: Dict[str, Dict[str, List[str]]] = {
    "3x3": {
        "likelihood_scale": ["Low", "Medium", "High"],
        "impact_scale": ["Low", "Medium", "High"]
    },
    "4x4": {
        "likelihood_scale": ["Very Low", "Low", "Medium", "High"],
        "impact_scale": ["Very Low", "Low", "Medium", "High"]
    },
    "5x5": {
        "likelihood_scale": ["Very Low", "Low", "Medium", "High", "Very High"],
        "impact_scale": ["Very Low", "Low", "Medium", "High", "Very High"]
    }
}

# Default Matrix
DEFAULT_MATRIX = "3x3"
DEFAULT_LIKELIHOOD_SCALE = MATRIX_CONFIGS[DEFAULT_MATRIX]["likelihood_scale"]
DEFAULT_IMPACT_SCALE = MATRIX_CONFIGS[DEFAULT_MATRIX]["impact_scale"]

# User Journey Stages
USER_STAGES = {
    "WELCOME": "welcome",
    "RISK_GENERATION": "risk_generation", 
    "RISK_EDITING": "risk_editing",
    "DATA_COLLECTION": "data_collection",
    "AWAITING_REPORT_APPROVAL": "awaiting_report_approval",
    "REPORT_READY": "report_ready"
}

# Risk Management
MAX_RISKS_PER_GENERATION = 10
MAX_GENERATED_RISKS_STORAGE = 50  # Per user
DEFAULT_RISK_FIELDS = [
    "description",
    "impact", 
    "likelihood",
    "treatment_strategy",
    "treatment_measures"
]

ADDITIONAL_RISK_FIELDS = [
    "asset_value",
    "department", 
    "risk_owner",
    "target_date",
    "risk_progress",
    "residual_exposure"
]

# Intent Classifications
USER_INTENTS = {
    "GENERAL_QUESTION": "general_question",
    "CHANGE_MATRIX": "change_matrix", 
    "GENERATE_RISKS": "generate_risks",
    "VIEW_RISKS": "view_risks",
    "FINALIZE_RISKS": "finalize_risks",
    "FILL_ADDITIONAL_DATA": "fill_additional_data",
    "GENERATE_REPORT": "generate_report",
    "APPROVE_REPORT": "approve_report",
    "REJECT_REPORT": "reject_report"
}

# LLM Configuration
LLM_CONTEXT_LIMITS = {
    "CONVERSATION_HISTORY": 10,  # Number of messages to keep
    "MAX_PROMPT_LENGTH": 4000,   # Characters
    "MAX_RESPONSE_LENGTH": 1000   # Characters
}

# Database Collections
COLLECTIONS = {
    "USERS": "users",
    "GENERATED_RISKS": "generated_risks", 
    "FINALIZED_RISKS": "finalized_risks",
    "RISK_REPORTS": "risk_reports"
}

# API Response Messages
RESPONSE_MESSAGES = {
    "USER_CREATED": "User registered successfully",
    "LOGIN_SUCCESS": "Login successful",
    "LOGIN_FAILED": "Invalid credentials",
    "USER_NOT_FOUND": "User not found",
    "RISKS_GENERATED": "Risks generated successfully",
    "RISKS_FINALIZED": "Risks finalized successfully", 
    "DATA_UPDATED": "Additional data updated successfully",
    "REPORT_GENERATED": "Risk report generated successfully",
    "MATRIX_UPDATED": "Risk matrix updated successfully",
    "INTERNAL_ERROR": "Internal server error occurred"
}

# Industry Categories (for risk generation context)
INDUSTRY_CATEGORIES = [
    "Technology",
    "Healthcare", 
    "Financial Services",
    "Manufacturing",
    "Retail",
    "Education",
    "Government",
    "Energy",
    "Transportation",
    "Real Estate",
    "Media & Entertainment",
    "Agriculture",
    "Other"
]

# Risk Categories (for generation guidance)
RISK_CATEGORIES = [
    "Operational",
    "Financial", 
    "Strategic",
    "Compliance",
    "Technology",
    "Reputation",
    "Market",
    "Environmental",
    "Human Resources",
    "Security"
]

# Popup Configuration
POPUP_TYPES = {
    "RISK_SELECTION": "risk_selection_popup",
    "DATA_COLLECTION": "data_collection_popup", 
    "CONFIRMATION": "confirmation_popup",
    "ERROR": "error_popup"
}

# Validation Rules
VALIDATION_RULES = {
    "USERNAME_MIN_LENGTH": 3,
    "USERNAME_MAX_LENGTH": 50,
    "PASSWORD_MIN_LENGTH": 6,
    "ORGANIZATION_MIN_LENGTH": 2,
    "ORGANIZATION_MAX_LENGTH": 100,
    "RISK_DESCRIPTION_MIN_LENGTH": 10,
    "RISK_DESCRIPTION_MAX_LENGTH": 500
}