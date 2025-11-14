"""
HuggingFace Inference API Client.

Provides access to free LLM models via HuggingFace Serverless Inference API.
Uses chat completions format for compatibility with deployed models.
"""

import requests
import logging
import json
from typing import Optional
from config.settings import Settings
from tools.rate_limiter import huggingface_rate_limit


class HuggingFaceAPIError(Exception):
    """Custom exception for HuggingFace API errors."""
    pass


class HuggingFaceClient:
    """
    Client for HuggingFace Serverless Inference API.

    Uses the free Serverless Inference API with chat completions format.
    Only works with models that have been deployed by inference providers.

    Confirmed working models:
    - google/gemma-2-2b-it (2B params, fast)
    - meta-llama/Meta-Llama-3-8B-Instruct (8B params, better quality)
    - Qwen/Qwen2.5-7B-Instruct (7B params, good reasoning)
    - mistralai/Mistral-7B-Instruct-v0.3 (7B params, excellent)

    Example:
        >>> client = HuggingFaceClient()
        >>> text = client.generate_text("Is Bitcoin bullish?")
        >>> print(text)
    """

    def __init__(self, model: str = "google/gemma-2-2b-it"):
        """
        Initialize HuggingFace client.

        Args:
            model: HuggingFace model ID that's deployed on inference API
                   (default: google/gemma-2-2b-it)
        """
        settings = Settings.get_instance()
        self.api_key = settings.HUGGINGFACE_API_KEY
        self.model = model

        # Correct endpoint for Serverless Inference with chat completions
        self.base_url = "https://router.huggingface.co/v1"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logging.info(f"[OK] HuggingFace client initialized: {model}")

    @huggingface_rate_limit
    def generate_text(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Generate text using HuggingFace model via chat completions API.

        Args:
            prompt: Text prompt for generation
            max_tokens: Maximum tokens to generate (default: 500)

        Returns:
            str: Generated text

        Raises:
            HuggingFaceAPIError: If API request fails
        """
        # Use chat completions endpoint
        url = f"{self.base_url}/chat/completions"

        # Chat completions format (required for deployed models)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1
        }

        try:
            logging.debug(f" HuggingFace request to: {url}")
            logging.debug(f"[DATA] Using model: {self.model}")

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )

            logging.debug(f"[DATA] Response status: {response.status_code}")

            # Check for errors
            if response.status_code != 200:
                error_msg = response.text[:500]
                raise HuggingFaceAPIError(
                    f"HuggingFace API Error {response.status_code}: {error_msg}"
                )

            # Parse JSON response (chat completions format)
            result = response.json()

            # Extract generated text from chat completions response
            if 'choices' in result and len(result['choices']) > 0:
                text = result['choices'][0]['message']['content']
            else:
                raise ValueError(f"Unexpected response format: {result}")

            logging.info(f"[OK] Generated {len(text)} characters")
            return text

        except requests.exceptions.JSONDecodeError as e:
            logging.error(f"[FAIL] HuggingFace API request failed: {e}")
            logging.error(f"Response text: {response.text[:500]}")
            raise HuggingFaceAPIError(f"Invalid JSON response: {e}")

        except requests.exceptions.RequestException as e:
            logging.error(f"[FAIL] Request failed: {e}")
            raise HuggingFaceAPIError(f"Request failed: {e}")

        except Exception as e:
            logging.error(f"[FAIL] HuggingFace API request failed: {e}")
            raise HuggingFaceAPIError(f"Request failed: {e}")

    def generate_json(self, prompt: str, max_tokens: int = 500) -> dict:
        """
        Generate text and parse as JSON.

        Args:
            prompt: Text prompt requesting JSON output
            max_tokens: Maximum tokens to generate

        Returns:
            dict: Parsed JSON response

        Raises:
            HuggingFaceAPIError: If generation or parsing fails
        """
        # Add JSON instruction to prompt
        json_prompt = f"{prompt}\n\nRespond with valid JSON only, no additional text."

        text = self.generate_text(json_prompt, max_tokens)

        # Strip markdown code blocks if present
        text = text.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from response: {text[:200]}")
            raise HuggingFaceAPIError(f"Response is not valid JSON: {e}")


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    client = HuggingFaceClient()
    print(f"Client initialized with base_url: {client.base_url}")
    print(f"Model: {client.model}")

    try:
        response = client.generate_text("What is Bitcoin?", max_tokens=50)
        print(f"[OK] Response: {response}")
    except Exception as e:
        print(f"[FAIL] Error: {e}")
