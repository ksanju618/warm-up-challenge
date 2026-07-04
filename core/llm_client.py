"""
Thin wrapper around the Gemini API (google-genai SDK).

Responsibilities:
- Load API key/model from environment only (never hardcoded).
- Enforce structured JSON output matching MealPlanLLMResponse via
  response_schema, so the model literally cannot return unstructured
  or off-schema hallucinated text.
- Retry transient failures with backoff.
- Surface clear, typed exceptions so calling code (and tests) can react
  predictably instead of guessing at string-matched errors.
"""

from __future__ import annotations

import os
import time
import logging

from google import genai
from google.genai import types

from core.schema import MealPlanLLMResponse

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.5


class LLMConfigError(RuntimeError):
    """Raised when required configuration (e.g. API key) is missing."""


class LLMGenerationError(RuntimeError):
    """Raised when the Gemini API call fails after retries, or returns
    content that doesn't validate against our schema."""


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise LLMConfigError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key, "
            "or export it as an environment variable."
        )
    return genai.Client(api_key=api_key)


def generate_structured_plan(system_instruction: str, user_prompt: str) -> MealPlanLLMResponse:
    """Call Gemini and return a validated MealPlanLLMResponse.

    Raises LLMConfigError if the API key is missing, or LLMGenerationError
    if the call fails after retries or the response fails schema validation.
    """
    client = _get_client()
    model_name = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=MealPlanLLMResponse,
        temperature=0.6,
    )

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=config,
            )
            raw_text = response.text
            if not raw_text:
                raise LLMGenerationError("Gemini returned an empty response.")

            # Validate against our schema explicitly, even though
            # response_schema already constrains the model -- this guards
            # against SDK/library version drift and is what makes this
            # logic unit-testable independent of the network call.
            return MealPlanLLMResponse.model_validate_json(raw_text)

        except Exception as exc:  # noqa: BLE001 - we deliberately re-wrap below
            last_error = exc
            logger.warning("Gemini call attempt %s/%s failed: %s", attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                time.sleep(BASE_BACKOFF_SECONDS * attempt)

    raise LLMGenerationError(
        f"Gemini API call failed after {MAX_RETRIES} attempts: {last_error}"
    ) from last_error
