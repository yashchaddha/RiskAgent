import logging
import sys
from datetime import datetime
from typing import Dict, Any
from config.settings import settings

class LoggingConfig:
    """Centralized logging configuration"""
    
    def __init__(self):
        self.log_level = getattr(logging, settings.log_level.upper())
        self.setup_logging()
    
    def setup_logging(self):
        """Setup application logging configuration"""
        
        # Create formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(self.log_level)
        
        # File handler (optional)
        if settings.debug:
            file_handler = logging.FileHandler(
                filename=f"logs/risk_agent_{datetime.now().strftime('%Y%m%d')}.log",
                mode='a'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        root_logger.addHandler(console_handler)
        
        if settings.debug:
            root_logger.addHandler(file_handler)
        
        # Set specific logger levels
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("motor").setLevel(logging.WARNING)
        logging.getLogger("pymongo").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get logger instance for specific module"""
        return logging.getLogger(name)
    
    def log_user_action(self, user_id: str, action: str, details: Dict[str, Any] = None):
        """Log user actions for audit trail"""
        logger = self.get_logger("user_actions")
        log_data = {
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        logger.info(f"User Action: {log_data}")
    
    def log_llm_call(self, user_id: str, intent: str, tokens_used: int, response_time: float):
        """Log LLM API calls for monitoring"""
        logger = self.get_logger("llm_calls")
        log_data = {
            "user_id": user_id,
            "intent": intent,
            "tokens_used": tokens_used,
            "response_time_ms": response_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.info(f"LLM Call: {log_data}")
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log errors with context"""
        logger = self.get_logger("errors")
        log_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.error(f"Application Error: {log_data}", exc_info=True)

# Global logging configuration instance
logging_config = LoggingConfig()

# Convenience function to get logger
def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return logging_config.get_logger(name)