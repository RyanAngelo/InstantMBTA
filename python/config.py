"""Configuration management for InstantMBTA."""

import os
import logging
from typing import Optional

logger = logging.getLogger('instantmbta.config')

class Config:
    """Configuration class for InstantMBTA."""
    
    def __init__(self):
        self.api_key = self._get_api_key()
        self.api_timeout = int(os.getenv('MBTA_API_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('MBTA_MAX_RETRIES', '5'))
        self.retry_delay = int(os.getenv('MBTA_RETRY_DELAY', '5'))
        self.log_level = os.getenv('MBTA_LOG_LEVEL', 'INFO')
    
    def _get_api_key(self) -> str:
        """Get API key from environment variable with validation."""
        api_key = os.getenv('MBTA_API_KEY')
        
        if not api_key:
            # For testing, provide a fallback
            if os.getenv('TESTING') == 'true':
                logger.warning("Using test API key for testing environment")
                return 'test_api_key_for_testing_only'
            
            error_msg = (
                "MBTA_API_KEY environment variable is not set. "
                "Please set it with: export MBTA_API_KEY='your_api_key_here'"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if api_key == 'test_api_key_for_testing_only':
            logger.warning(
                "Using test API key. For production, set a real MBTA_API_KEY "
                "environment variable."
            )
        
        # Basic validation - API keys should be non-empty and not too short
        if len(api_key) < 10:
            logger.warning("API key seems too short. Please verify it's correct.")
        
        return api_key
    
    def validate(self) -> bool:
        """Validate configuration."""
        try:
            if not self.api_key:
                return False
            if self.api_timeout <= 0:
                logger.error("API timeout must be positive")
                return False
            if self.max_retries < 0:
                logger.error("Max retries cannot be negative")
                return False
            if self.retry_delay <= 0:
                logger.error("Retry delay must be positive")
                return False
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

# Global configuration instance
config = Config() 