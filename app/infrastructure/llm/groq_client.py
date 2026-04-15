"""
Groq LLM client - supports llama3-70b, llama3-8b, mixtral-8x7b.
Implements retry logic, fallback, and structured output enforcement.
"""
from __future__ import annotations
import asyncio
import json
import re
import time
from typing import Any, Optional
from groq import AsyncGroq, APIError, RateLimitError, APITimeoutError
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GroqClient:
    """
    Production-grade async Groq client with:
    - Automatic retry with exponential backoff
    - Model fallback chain
    - Structured JSON output extraction
    - Token usage logging
    """

    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.primary_model = settings.GROQ_MODEL_PRIMARY
        self.fast_model = settings.GROQ_MODEL_FAST
        self.analysis_model = settings.GROQ_MODEL_ANALYSIS

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = None,
        max_tokens: int = None,
        json_mode: bool = False,
    ) -> str:
        """
        Call Groq API with retry and fallback.
        Returns the text content of the response.
        """
        target_model = model or self.primary_model
        temp = temperature if temperature is not None else settings.GROQ_TEMPERATURE
        tokens = max_tokens or settings.GROQ_MAX_TOKENS

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_error = None
        for attempt in range(settings.GROQ_MAX_RETRIES):
            try:
                start = time.monotonic()
                response = await self.client.chat.completions.create(**kwargs)
                elapsed = (time.monotonic() - start) * 1000

                content = response.choices[0].message.content
                usage = response.usage

                logger.info(
                    "Groq LLM call succeeded",
                    extra={
                        "extra_data": {
                            "model": target_model,
                            "attempt": attempt + 1,
                            "latency_ms": round(elapsed, 2),
                            "input_tokens": usage.prompt_tokens if usage else 0,
                            "output_tokens": usage.completion_tokens if usage else 0,
                        }
                    },
                )
                return content

            except RateLimitError as e:
                last_error = e
                wait_time = settings.GROQ_RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Groq rate limit hit, retrying in {wait_time}s (attempt {attempt+1})")
                await asyncio.sleep(wait_time)

            except APITimeoutError as e:
                last_error = e
                wait_time = settings.GROQ_RETRY_DELAY * (attempt + 1)
                logger.warning(f"Groq timeout, retrying in {wait_time}s (attempt {attempt+1})")
                await asyncio.sleep(wait_time)

                # Fallback to faster model on timeout
                if attempt == 1 and target_model == self.primary_model:
                    target_model = self.fast_model
                    kwargs["model"] = target_model
                    logger.info(f"Falling back to model: {target_model}")

            except APIError as e:
                last_error = e
                logger.error(f"Groq API error: {e}", exc_info=True)
                if attempt < settings.GROQ_MAX_RETRIES - 1:
                    await asyncio.sleep(settings.GROQ_RETRY_DELAY)
                else:
                    raise

        raise RuntimeError(f"Groq LLM failed after {settings.GROQ_MAX_RETRIES} attempts: {last_error}")

    async def extract_json(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        schema_hint: Optional[str] = None,
    ) -> dict:
        """
        Call LLM and extract JSON from response.
        Uses json_mode when available, falls back to regex extraction.
        """
        if schema_hint:
            system_prompt = f"{system_prompt}\n\nYou MUST respond with valid JSON only. Schema:\n{schema_hint}"

        full_system = (
            f"{system_prompt}\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "No markdown, no code fences, no explanation. Just the JSON object."
        )

        try:
            content = await self.complete(
                prompt=prompt,
                system_prompt=full_system,
                model=model,
                json_mode=True,
            )
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            return self._extract_json_from_text(content)
        except Exception as e:
            logger.error(f"JSON extraction failed: {e}", exc_info=True)
            raise

    def _extract_json_from_text(self, text: str) -> dict:
        """Extract JSON from text that may contain markdown or other content."""
        # Try json code block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))

        # Try bare JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))

        raise ValueError(f"Could not extract JSON from LLM response: {text[:500]}")

    async def complete_analysis(self, prompt: str, system_prompt: str = "") -> str:
        """Use the analysis model (mixtral) for complex reasoning tasks."""
        return await self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.analysis_model,
        )


# Singleton
_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
