"""Configuration module for the Bitcoin trading system.

This module contains configuration management, environment variables,
and service account credentials handling.

Files in this directory:
- .env.example: Environment variables template
- config.json: Runtime configuration (trading params, API keys, etc.)
- service_account.json: Google Sheets API credentials
- settings.py: Configuration loader and validator
- llm_config.py: LLM model configuration and fallback chains
- constants.py: System-wide constants and enums

Example:
    >>> from config import get_settings, get_primary_model_config
    >>> settings = get_settings()
    >>> model = get_primary_model_config()
"""

from typing import List

# Import main configuration functions for easy access
from config.settings import Settings, get_settings
from config.llm_config import (
    LLMConfig,
    ModelProvider,
    ModelRole,
    get_primary_model_config,
    get_fallback_models,
    get_agent_config,
    create_model_chain,
)

__all__: List[str] = [
    # Settings
    "Settings",
    "get_settings",
    # LLM Configuration
    "LLMConfig",
    "ModelProvider",
    "ModelRole",
    "get_primary_model_config",
    "get_fallback_models",
    "get_agent_config",
    "create_model_chain",
]
