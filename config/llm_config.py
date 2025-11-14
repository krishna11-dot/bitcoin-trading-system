"""LLM configuration for the Bitcoin trading system.

This module provides configuration for Large Language Models used by the
trading agents. It defines model settings, fallback chains, and parameters
optimized for trading decision-making.

The system uses free/open-source LLMs to minimize operational costs while
maintaining high-quality decision-making capabilities.

Example:
    >>> from config.llm_config import get_primary_model_config, get_fallback_models
    >>> primary = get_primary_model_config()
    >>> print(primary.model_name)
    'google/flan-t5-base'
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ModelProvider(str, Enum):
    """Enum for LLM provider types."""

    HUGGINGFACE = "huggingface"
    OPENROUTER = "openrouter"
    LOCAL = "local"


class ModelRole(str, Enum):
    """Enum for model usage roles in the system."""

    # Primary model for critical analysis and decision-making
    PRIMARY = "primary"

    # Fast fallback for when primary is unavailable
    FALLBACK_FAST = "fallback_fast"

    # Reliable fallback with good reasoning
    FALLBACK_RELIABLE = "fallback_reliable"

    # Emergency fallback (local or ultra-fast)
    FALLBACK_EMERGENCY = "fallback_emergency"


@dataclass
class LLMConfig:
    """Configuration for a specific LLM model.

    Attributes:
        model_name: Full model identifier (e.g., "google/flan-t5-base")
        provider: Model provider (HUGGINGFACE, OPENROUTER, LOCAL)
        role: Model's role in the system (PRIMARY, FALLBACK_FAST, etc.)
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
        max_tokens: Maximum tokens to generate in response
        top_p: Nucleus sampling parameter (0.0-1.0)
        frequency_penalty: Penalty for token frequency (reduces repetition)
        presence_penalty: Penalty for token presence (encourages diversity)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        description: Human-readable description of model capabilities
        use_case: Specific use cases where this model excels
    """

    model_name: str
    provider: ModelProvider
    role: ModelRole
    temperature: float = 0.1  # Low temperature for consistent trading decisions
    max_tokens: int = 500  # Concise responses for faster decision-making
    top_p: float = 0.95
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 30  # seconds
    max_retries: int = 3
    description: str = ""
    use_case: str = ""

    def __post_init__(self) -> None:
        """Validate LLM configuration parameters.

        Raises:
            ValueError: If configuration parameters are invalid
        """
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"temperature must be between 0.0 and 2.0 (got {self.temperature})")

        if self.max_tokens < 1:
            raise ValueError(f"max_tokens must be at least 1 (got {self.max_tokens})")

        if not 0.0 <= self.top_p <= 1.0:
            raise ValueError(f"top_p must be between 0.0 and 1.0 (got {self.top_p})")

        if self.timeout < 1:
            raise ValueError(f"timeout must be at least 1 second (got {self.timeout})")

        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative (got {self.max_retries})")

    def to_dict(self) -> Dict[str, any]:
        """Convert configuration to dictionary for API calls.

        Returns:
            Dict[str, any]: Configuration parameters as dictionary
        """
        return {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }


# ============================================================================
# Primary Model Configuration
# ============================================================================

PRIMARY_MODEL = LLMConfig(
    model_name="google/gemma-2-2b-it",
    provider=ModelProvider.HUGGINGFACE,
    role=ModelRole.PRIMARY,
    temperature=0.1,  # Low for deterministic trading decisions
    max_tokens=500,  # Sufficient for detailed analysis
    top_p=0.95,
    description="Primary model for market analysis and strategic decision-making. "
    "Gemma-2-2b is fast, reliable, and confirmed available on free inference API.",
    use_case="Market analysis, risk assessment, strategy selection",
)


# ============================================================================
# Fallback Model Configurations
# ============================================================================

FALLBACK_MODELS = [
    # Fast fallback - Mistral 7B via OpenRouter
    LLMConfig(
        model_name="mistralai/mistral-7b-instruct:free",
        provider=ModelProvider.OPENROUTER,
        role=ModelRole.FALLBACK_FAST,
        temperature=0.1,
        max_tokens=500,
        top_p=0.95,
        timeout=20,  # Faster timeout for quick fallback
        description="Fast fallback model via OpenRouter. Good for quick decisions "
        "when primary model is unavailable.",
        use_case="Quick market checks, simple execution decisions",
    ),
    # Reliable fallback - FLAN-T5 Large
    LLMConfig(
        model_name="google/flan-t5-large",
        provider=ModelProvider.HUGGINGFACE,
        role=ModelRole.FALLBACK_RELIABLE,
        temperature=0.1,
        max_tokens=500,
        top_p=0.95,
        description="Reliable fallback with stronger capabilities than base model. "
        "FLAN-T5-Large provides better reasoning for complex analysis.",
        use_case="Market analysis, risk assessment when primary unavailable",
    ),
    # Alternative fallback - GPT-2
    LLMConfig(
        model_name="gpt2",
        provider=ModelProvider.HUGGINGFACE,
        role=ModelRole.FALLBACK_RELIABLE,
        temperature=0.1,
        max_tokens=500,
        top_p=0.95,
        description="Alternative reliable fallback. GPT-2 is widely available "
        "and provides good text generation.",
        use_case="Technical analysis, general text generation",
    ),
    # Emergency fallback - DistilGPT2
    LLMConfig(
        model_name="distilgpt2",
        provider=ModelProvider.HUGGINGFACE,
        role=ModelRole.FALLBACK_EMERGENCY,
        temperature=0.1,
        max_tokens=500,
        top_p=0.95,
        timeout=15,  # Very fast timeout for emergency
        description="Emergency fallback when all other models fail. "
        "Lightweight and fast for basic decisions.",
        use_case="Emergency decisions, system health checks",
    ),
]


# ============================================================================
# Agent-Specific Model Configurations
# ============================================================================

AGENT_MODEL_PREFERENCES = {
    # Market Analyst: Needs strong reasoning for complex market analysis
    "market_analyst": {
        "primary": PRIMARY_MODEL,
        "fallbacks": [FALLBACK_MODELS[0], FALLBACK_MODELS[1]],  # Mistral, Llama
        "temperature": 0.1,  # Deterministic for consistent analysis
        "max_tokens": 500,
    },
    # Risk Manager: Requires precise calculations and conservative approach
    "risk_manager": {
        "primary": PRIMARY_MODEL,
        "fallbacks": [FALLBACK_MODELS[1], FALLBACK_MODELS[0]],  # Llama, Mistral
        "temperature": 0.05,  # Very low for risk-averse decisions
        "max_tokens": 400,
    },
    # Strategy Selector: Needs balanced reasoning for strategy choice
    "strategy_selector": {
        "primary": PRIMARY_MODEL,
        "fallbacks": [FALLBACK_MODELS[2], FALLBACK_MODELS[0]],  # Qwen, Mistral
        "temperature": 0.1,
        "max_tokens": 400,
    },
    # Execution Agent: Fast decisions, less analysis needed
    "execution_agent": {
        "primary": FALLBACK_MODELS[0],  # Use fast Mistral as primary
        "fallbacks": [FALLBACK_MODELS[3], PRIMARY_MODEL],  # Emergency then full model
        "temperature": 0.05,  # Very deterministic for execution
        "max_tokens": 300,  # Shorter responses for quick execution
    },
    # Supervisor: High-level orchestration, needs good reasoning
    "supervisor": {
        "primary": PRIMARY_MODEL,
        "fallbacks": [FALLBACK_MODELS[1], FALLBACK_MODELS[0]],  # Llama, Mistral
        "temperature": 0.15,  # Slightly higher for coordination flexibility
        "max_tokens": 600,
    },
}


# ============================================================================
# Model Configuration Functions
# ============================================================================


def get_primary_model_config() -> LLMConfig:
    """Get the primary model configuration.

    Returns:
        LLMConfig: Primary model configuration

    Example:
        >>> config = get_primary_model_config()
        >>> print(config.model_name)
        'google/flan-t5-base'
    """
    return PRIMARY_MODEL


def get_fallback_models() -> List[LLMConfig]:
    """Get list of fallback models in priority order.

    Returns:
        List[LLMConfig]: Fallback models ordered by priority

    Example:
        >>> fallbacks = get_fallback_models()
        >>> print(len(fallbacks))
        4
    """
    return FALLBACK_MODELS.copy()


def get_agent_config(agent_name: str) -> Dict[str, any]:
    """Get model configuration for a specific agent.

    Args:
        agent_name: Name of the agent (e.g., 'market_analyst', 'risk_manager')

    Returns:
        Dict[str, any]: Agent-specific model configuration

    Raises:
        KeyError: If agent_name is not recognized

    Example:
        >>> config = get_agent_config('market_analyst')
        >>> print(config['primary'].model_name)
        'google/flan-t5-base'
    """
    if agent_name not in AGENT_MODEL_PREFERENCES:
        raise KeyError(
            f"Unknown agent: {agent_name}. "
            f"Valid agents: {', '.join(AGENT_MODEL_PREFERENCES.keys())}"
        )

    return AGENT_MODEL_PREFERENCES[agent_name].copy()


def get_model_by_role(role: ModelRole) -> Optional[LLMConfig]:
    """Get model configuration by role.

    Args:
        role: Model role (PRIMARY, FALLBACK_FAST, etc.)

    Returns:
        Optional[LLMConfig]: Model configuration or None if not found

    Example:
        >>> config = get_model_by_role(ModelRole.PRIMARY)
        >>> print(config.model_name)
        'google/flan-t5-base'
    """
    if role == ModelRole.PRIMARY:
        return PRIMARY_MODEL

    for model in FALLBACK_MODELS:
        if model.role == role:
            return model

    return None


def create_model_chain(agent_name: str) -> List[LLMConfig]:
    """Create a prioritized model chain for an agent.

    Returns the primary model followed by fallbacks in priority order.
    This enables automatic failover when models are unavailable.

    Args:
        agent_name: Name of the agent

    Returns:
        List[LLMConfig]: Ordered list of models to try

    Example:
        >>> chain = create_model_chain('risk_manager')
        >>> for model in chain:
        ...     print(model.model_name)
        google/flan-t5-base
        google/flan-t5-large
        mistralai/mistral-7b-instruct:free
    """
    config = get_agent_config(agent_name)
    chain = [config["primary"]] + config["fallbacks"]
    return chain


# ============================================================================
# Validation
# ============================================================================


def validate_all_configs() -> None:
    """Validate all model configurations.

    Raises:
        ValueError: If any configuration is invalid
    """
    # Validate primary model
    PRIMARY_MODEL.__post_init__()

    # Validate all fallback models
    for model in FALLBACK_MODELS:
        model.__post_init__()

    print("All LLM configurations validated successfully.")


# Validate on module import
if __name__ != "__main__":
    validate_all_configs()
