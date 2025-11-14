"""OpenRouter API client for LLM inference (backup for HuggingFace).

This module provides a wrapper around the OpenRouter API with rate limiting
and JSON parsing. OpenRouter provides access to free models like Mistral-7B.

Example:
    >>> from tools.openrouter_client import OpenRouterClient
    >>> client = OpenRouterClient()
    >>> response = client.generate_text("Analyze BTC: price dropped 3%")
    >>> print(response)
"""

import json
import logging
import time
from typing import Any, Dict, Optional

import requests

from config import get_settings
from tools.rate_limiter import openrouter_rate_limit


# Configure logger
logger = logging.getLogger(__name__)


class OpenRouterClientError(Exception):
    """Base exception for OpenRouter client errors."""

    pass


class OpenRouterAPIError(OpenRouterClientError):
    """Raised when OpenRouter API returns an error response."""

    def __init__(self, status_code: int, message: str):
        """Initialize OpenRouter API error.

        Args:
            status_code: HTTP status code
            message: Error message from API
        """
        self.status_code = status_code
        self.message = message
        super().__init__(f"OpenRouter API Error {status_code}: {message}")


class OpenRouterClient:
    """Client for interacting with OpenRouter API.

    This client provides methods for text generation and JSON-structured outputs
    using free models available on OpenRouter (primarily Mistral-7B).

    Attributes:
        api_key: OpenRouter API key
        model: Model name (default: mistralai/mistral-7b-instruct:free)

    Example:
        >>> client = OpenRouterClient()
        >>> text = client.generate_text("What is DCA?", max_tokens=100)
        >>> print(text)
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mistralai/mistral-7b-instruct:free",
    ):
        """Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key (defaults to config)
            model: Model name (default: mistralai/mistral-7b-instruct:free)
        """
        settings = get_settings()

        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model

        if not self.api_key:
            raise OpenRouterClientError(
                "OpenRouter API key not configured. Set OPENROUTER_API_KEY in .env"
            )

        logger.info(f"Initialized OpenRouterClient (model={self.model})")

    def _make_request(
        self,
        messages: list,
        max_tokens: int = 500,
        temperature: float = 0.1,
        max_retries: int = 2,
    ) -> str:
        """Make HTTP request to OpenRouter API.

        Args:
            messages: List of message dictionaries (OpenAI chat format)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            max_retries: Maximum number of retry attempts

        Returns:
            str: Generated text

        Raises:
            OpenRouterAPIError: If API returns error response
            OpenRouterClientError: If request fails after retries
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/bitcoin-trading-system",  # Optional
            "X-Title": "Bitcoin Trading System",  # Optional
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"OpenRouter API: {self.model} (attempt {attempt + 1}/{max_retries})"
                )

                response = requests.post(
                    self.API_URL, json=payload, headers=headers, timeout=30
                )

                if response.status_code == 429:
                    # Rate limit exceeded
                    logger.warning("OpenRouter rate limit exceeded, waiting...")
                    time.sleep(10 * (attempt + 1))
                    continue

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    raise OpenRouterAPIError(
                        status_code=response.status_code,
                        message=error_msg,
                    )

                data = response.json()

                # Extract generated text
                if "choices" in data and len(data["choices"]) > 0:
                    message = data["choices"][0].get("message", {})
                    generated_text = message.get("content", "")

                    logger.info(f"[OK] Generated {len(generated_text)} characters")
                    return generated_text
                else:
                    raise OpenRouterClientError(f"Unexpected response format: {data}")

            except requests.exceptions.Timeout:
                logger.warning(f"OpenRouter API timeout (attempt {attempt + 1})")
                if attempt == max_retries - 1:
                    raise OpenRouterClientError("Request timed out after retries")
                time.sleep(2**attempt)

            except requests.exceptions.RequestException as e:
                logger.error(f"OpenRouter API request failed: {e}")
                if attempt == max_retries - 1:
                    raise OpenRouterClientError(f"Request failed: {e}")
                time.sleep(2**attempt)

            except OpenRouterAPIError:
                # Don't retry API errors
                raise

        raise OpenRouterClientError("Unexpected error in request logic")

    @openrouter_rate_limit
    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.1,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate text using OpenRouter API.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system_prompt: Optional system prompt

        Returns:
            str: Generated text

        Raises:
            OpenRouterClientError: If request fails

        Example:
            >>> client = OpenRouterClient()
            >>> text = client.generate_text("Explain swing trading")
            >>> print(text)
        """
        logger.info(f"Generating text (prompt_length={len(prompt)})")

        # Build messages in OpenAI chat format
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        # Generate
        try:
            response = self._make_request(messages, max_tokens, temperature)
            logger.info("[OK] Text generation successful")
            return response

        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise

    @openrouter_rate_limit
    def generate_json(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.1,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate JSON-structured output with error handling.

        Args:
            prompt: Input prompt (should request JSON output)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system_prompt: Optional system prompt

        Returns:
            Dict: Parsed JSON response

        Raises:
            OpenRouterClientError: If generation or parsing fails

        Example:
            >>> client = OpenRouterClient()
            >>> prompt = "Return JSON: {signal: buy/sell/hold, reason: str}"
            >>> result = client.generate_json(prompt)
            >>> print(result["signal"])
        """
        logger.info(f"Generating JSON (prompt_length={len(prompt)})")

        # Add JSON instruction to prompt if not present
        if "json" not in prompt.lower():
            prompt = f"{prompt}\n\nRespond with valid JSON only."

        # Add system prompt for JSON
        if not system_prompt:
            system_prompt = "You are a helpful assistant that responds in valid JSON format."

        # Generate text
        response_text = self.generate_text(prompt, max_tokens, temperature, system_prompt)

        # Parse JSON from response
        try:
            # Try to extract JSON from response (handle markdown code blocks)
            json_str = response_text.strip()

            # Remove markdown code block markers if present
            if json_str.startswith("```"):
                lines = json_str.split("\n")
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line (```)
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                json_str = "\n".join(lines)

            # Parse JSON
            parsed_json = json.loads(json_str)

            logger.info("[OK] Successfully parsed JSON response")
            return parsed_json

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")

            # Return error dict instead of raising
            return {
                "error": "Failed to parse JSON",
                "raw_response": response_text[:500],
            }

    def get_model_info(self) -> Dict[str, str]:
        """Get information about the current model.

        Returns:
            Dict with model information

        Example:
            >>> client = OpenRouterClient()
            >>> info = client.get_model_info()
            >>> print(f"Model: {info['name']}")
        """
        return {
            "name": self.model,
            "provider": "OpenRouter",
            "description": "Free tier access to Mistral-7B-Instruct",
            "rate_limit": "15 calls per 60 seconds",
        }

    def __repr__(self) -> str:
        """Return string representation of client.

        Returns:
            str: Client representation
        """
        return f"OpenRouterClient(model={self.model})"
