from abc import ABC, abstractmethod
from typing import AsyncGenerator

class LLMProvider(ABC):
    """
    Abstract interface for LLM client providers.
    Enables future support for other cloud providers (e.g. OpenAI, Anthropic) without rewriting.
    """
    @abstractmethod
    async def generate(self, system_instruction: str, prompt: str) -> str:
        """
        Runs synchronous content generation.
        """
        pass

    @abstractmethod
    async def stream(self, system_instruction: str, prompt: str) -> AsyncGenerator[str, None]:
        """
        Yields text chunks progressively in real-time.
        """
        pass
