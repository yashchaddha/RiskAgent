from config.settings import settings
from config.constants import (
    MATRIX_CONFIGS, 
    DEFAULT_MATRIX,
    USER_STAGES,
    USER_INTENTS,
    RESPONSE_MESSAGES,
    COLLECTIONS,
    VALIDATION_RULES,
    POPUP_TYPES,
    MAX_GENERATED_RISKS_STORAGE,
)
from config.llm_config import llm_config, SYSTEM_MESSAGES
from config.logging import logging_config, get_logger

# Utility functions
def get_matrix_scales(matrix_size: str) -> dict:
    """Get likelihood and impact scales for given matrix size"""
    if matrix_size not in MATRIX_CONFIGS:
        matrix_size = DEFAULT_MATRIX
    return MATRIX_CONFIGS[matrix_size]

def validate_matrix_size(matrix_size: str) -> bool:
    """Validate if matrix size is supported"""
    return matrix_size in MATRIX_CONFIGS

def get_available_matrix_sizes() -> list:
    """Get list of available matrix sizes"""
    return list(MATRIX_CONFIGS.keys())

def get_system_message(task_type: str) -> str:
    """Get system message for specific task type"""
    return SYSTEM_MESSAGES.get(task_type, SYSTEM_MESSAGES["general_qa"])

def validate_user_input(field: str, value: str) -> bool:
    """Validate user input based on field rules"""
    rules = VALIDATION_RULES
    
    if field == "username":
        return rules["USERNAME_MIN_LENGTH"] <= len(value) <= rules["USERNAME_MAX_LENGTH"]
    elif field == "password":
        return len(value) >= rules["PASSWORD_MIN_LENGTH"]
    elif field == "organization":
        return rules["ORGANIZATION_MIN_LENGTH"] <= len(value) <= rules["ORGANIZATION_MAX_LENGTH"]
    elif field == "risk_description":
        return rules["RISK_DESCRIPTION_MIN_LENGTH"] <= len(value) <= rules["RISK_DESCRIPTION_MAX_LENGTH"]
    
    return True

def get_collection_name(collection_type: str) -> str:
    """Get MongoDB collection name"""
    return COLLECTIONS.get(collection_type.upper(), collection_type)

def get_response_message(message_type: str) -> str:
    """Get standard response message"""
    return RESPONSE_MESSAGES.get(message_type.upper(), "Operation completed")

# Export commonly used items
__all__ = [
    "settings",
    "llm_config", 
    "logging",
    "get_logger",
    "MATRIX_CONFIGS",
    "USER_STAGES",
    "USER_INTENTS",
    "SYSTEM_MESSAGES",
    "get_matrix_scales",
    "validate_matrix_size",
    "get_available_matrix_sizes",
    "get_system_message",
    "validate_user_input",
    "get_collection_name",
    "get_response_message",
    "POPUP_TYPES",
    "MAX_GENERATED_RISKS_STORAGE"
]