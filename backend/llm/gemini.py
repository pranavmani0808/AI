from google import genai
from google.genai import types
from typing import AsyncGenerator
from backend.core.config import settings
from backend.llm.provider import LLMProvider

class GeminiProvider(LLMProvider):
    """
    Google GenAI SDK provider wrapper.
    Implements abstract LLMProvider using the standard client.aio interface.
    """
    def __init__(self):
        self._client = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                raise ValueError("GEMINI_API_KEY configuration variable is missing or empty.")
            self._client = genai.Client(api_key=api_key)
        return self._client

    async def generate(self, system_instruction: str, prompt: str) -> str:
        """
        Executes standard async text generation with exponential backoff on rate limits.
        """
        client = self._get_client()
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0,
        )
        
        max_attempts = 4
        delay = 3.0
        for attempt in range(max_attempts):
            try:
                response = await client.aio.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=config
                )
                return response.text or ""
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "unavailable" in err_str
                if is_rate_limit and attempt < max_attempts - 1:
                    print(f"Gemini API rate limit/busy encountered. Sleeping {delay}s before retry (attempt {attempt + 1}/{max_attempts})...")
                    import asyncio
                    await asyncio.sleep(delay)
                    delay *= 2.0
                    continue
                print(f"Gemini generate API call failed: {e}")
                raise e

    async def stream(self, system_instruction: str, prompt: str) -> AsyncGenerator[str, None]:
        """
        Yields text tokens progressively with retry backoff safety.
        """
        client = self._get_client()
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0,
        )
        
        max_attempts = 4
        delay = 3.0
        response_stream = None
        for attempt in range(max_attempts):
            try:
                response_stream = await client.aio.models.generate_content_stream(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=config
                )
                break
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "unavailable" in err_str
                if is_rate_limit and attempt < max_attempts - 1:
                    print(f"Gemini API stream rate limit/busy encountered. Sleeping {delay}s before retry (attempt {attempt + 1}/{max_attempts})...")
                    import asyncio
                    await asyncio.sleep(delay)
                    delay *= 2.0
                    continue
                print(f"Gemini stream API call failed: {e}")
                raise e
                
        if response_stream:
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
