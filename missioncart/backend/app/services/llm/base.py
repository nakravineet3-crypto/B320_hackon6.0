from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    latency_ms: float
    cached: bool = False
    tokens_used: int = 0


class BaseLLMClient(ABC):
    """Abstract base for all LLM providers.
    Every provider implements exactly one method: complete()
    """

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 500,
        temperature: float = 0.1,
    ) -> LLMResponse:
        pass

    def _timed_call(self, fn, *args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        latency = (time.perf_counter() - start) * 1000
        return result, latency
