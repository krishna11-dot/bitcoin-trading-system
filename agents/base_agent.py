"""Base agent class for all trading system agents.

This module provides the abstract base class that all specialized agents inherit from.
It handles LLM client management, prompt loading, and fallback logic.

Example:
    >>> from agents.base_agent import BaseAgent
    >>> class MyAgent(BaseAgent):
    ...     def execute(self, data):
    ...         prompt = self.load_prompt("my_prompt.txt", price=data.price)
    ...         return self.generate_text(prompt)
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from config.llm_config import PRIMARY_MODEL, FALLBACK_MODELS, ModelProvider
from tools import HuggingFaceClient, OpenRouterClient
from tools import HuggingFaceAPIError, OpenRouterClientError


logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Base exception for agent errors."""
    pass


class BaseAgent(ABC):
    """Abstract base class for all agents in the trading system.

    This class provides common functionality for all agents:
    - LLM client management with automatic fallback
    - Prompt template loading from external files
    - Error handling and retry logic
    - Logging and monitoring hooks

    Attributes:
        agent_name: Name of the agent (for logging)
        prompts_dir: Directory containing prompt templates

    Example:
        >>> class MarketAnalyst(BaseAgent):
        ...     def execute(self, market_data):
        ...         prompt = self.load_prompt("analyze_market.txt",
        ...                                    price=market_data.price)
        ...         return self.generate_json(prompt)
    """

    def __init__(self, agent_name: str, prompts_dir: Optional[Path] = None):
        """Initialize base agent.

        Args:
            agent_name: Name of the agent (used for logging)
            prompts_dir: Directory containing prompt templates (defaults to prompts/)
        """
        self.agent_name = agent_name
        self.prompts_dir = prompts_dir or Path(__file__).parent.parent / "prompts"

        # Initialize primary LLM client
        self.primary_client = self._initialize_primary_client()
        self.fallback_clients = self._initialize_fallback_clients()

        logger.info(f"[OK] {self.agent_name} initialized with {len(self.fallback_clients)} fallback models")

    def _initialize_primary_client(self):
        """Initialize primary LLM client based on config.

        Returns:
            Primary LLM client instance
        """
        if PRIMARY_MODEL.provider == ModelProvider.HUGGINGFACE:
            return HuggingFaceClient(model=PRIMARY_MODEL.model_name)
        elif PRIMARY_MODEL.provider == ModelProvider.OPENROUTER:
            return OpenRouterClient(model=PRIMARY_MODEL.model_name)
        else:
            raise AgentError(f"Unsupported provider: {PRIMARY_MODEL.provider}")

    def _initialize_fallback_clients(self) -> list:
        """Initialize fallback LLM clients.

        Returns:
            List of fallback client instances
        """
        clients = []
        for model_config in FALLBACK_MODELS:
            try:
                if model_config.provider == ModelProvider.HUGGINGFACE:
                    clients.append(HuggingFaceClient(model=model_config.model_name))
                elif model_config.provider == ModelProvider.OPENROUTER:
                    clients.append(OpenRouterClient(model=model_config.model_name))
            except Exception as e:
                logger.warning(f"Failed to initialize fallback client {model_config.model_name}: {e}")

        return clients

    def load_prompt(self, template_name: str, **kwargs) -> str:
        """Load prompt template from file and format with variables.

        Args:
            template_name: Name of prompt template file (e.g., "analyze_market.txt")
            **kwargs: Variables to format into the template

        Returns:
            str: Formatted prompt ready for LLM

        Raises:
            AgentError: If template file not found or formatting fails

        Example:
            >>> prompt = self.load_prompt("analyze.txt", price=50000, rsi=65)
        """
        template_path = self.prompts_dir / template_name

        if not template_path.exists():
            raise AgentError(f"Prompt template not found: {template_path}")

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()

            # Format template with provided variables
            formatted_prompt = template.format(**kwargs)

            logger.debug(f"[NOTE] Loaded prompt template: {template_name}")
            return formatted_prompt

        except KeyError as e:
            raise AgentError(f"Missing template variable: {e}")
        except Exception as e:
            raise AgentError(f"Failed to load prompt template: {e}")

    def generate_text(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate text using LLM with automatic fallback.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate

        Returns:
            str: Generated text

        Raises:
            AgentError: If all LLM clients fail
        """
        # Try primary client
        try:
            logger.debug(f"[SYSTEM] {self.agent_name}: Calling primary LLM")
            return self.primary_client.generate_text(prompt, max_tokens=max_tokens)
        except (HuggingFaceAPIError, OpenRouterClientError) as e:
            logger.warning(f"Primary LLM failed: {e}, trying fallbacks...")

        # Try fallback clients
        for i, fallback_client in enumerate(self.fallback_clients):
            try:
                logger.debug(f"[PROCESSING] {self.agent_name}: Trying fallback {i+1}/{len(self.fallback_clients)}")
                return fallback_client.generate_text(prompt, max_tokens=max_tokens)
            except Exception as e:
                logger.warning(f"Fallback {i+1} failed: {e}")
                continue

        # All clients failed
        raise AgentError(f"{self.agent_name}: All LLM clients failed")

    def generate_json(self, prompt: str, max_tokens: int = 500) -> Dict[str, Any]:
        """Generate JSON output using LLM with automatic fallback.

        Args:
            prompt: Input prompt (should request JSON output)
            max_tokens: Maximum tokens to generate

        Returns:
            Dict: Parsed JSON response

        Raises:
            AgentError: If all LLM clients fail or JSON parsing fails
        """
        # Try primary client
        try:
            logger.debug(f"[SYSTEM] {self.agent_name}: Calling primary LLM for JSON")
            return self.primary_client.generate_json(prompt, max_tokens=max_tokens)
        except (HuggingFaceAPIError, OpenRouterClientError) as e:
            logger.warning(f"Primary LLM failed: {e}, trying fallbacks...")

        # Try fallback clients
        for i, fallback_client in enumerate(self.fallback_clients):
            try:
                logger.debug(f"[PROCESSING] {self.agent_name}: Trying fallback {i+1}/{len(self.fallback_clients)}")
                return fallback_client.generate_json(prompt, max_tokens=max_tokens)
            except Exception as e:
                logger.warning(f"Fallback {i+1} failed: {e}")
                continue

        # All clients failed
        raise AgentError(f"{self.agent_name}: All LLM clients failed for JSON generation")

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the agent's main task.

        This method must be implemented by all subclasses.

        Args:
            *args: Task-specific arguments
            **kwargs: Task-specific keyword arguments

        Returns:
            Task-specific output
        """
        pass

    def __repr__(self) -> str:
        """Return string representation of agent.

        Returns:
            str: Agent representation
        """
        return f"{self.__class__.__name__}(agent_name={self.agent_name})"
