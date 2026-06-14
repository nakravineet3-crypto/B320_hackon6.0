import hashlib
import json
import time
import os
from typing import Optional
from cachetools import TTLCache
import diskcache


class PromptCache:
    """Two-level cache:
    L1 — in-memory TTLCache (fast, limited size)
    L2 — disk cache (persistent across restarts)

    Cache key = hash(system_prompt + user_message)
    TTL = 1 hour (goal parsing is deterministic enough)

    Why this matters for throughput:
    - Same goal typed twice → instant response
    - Warm demo → zero LLM latency on repeated runs
    - Saves API credits during testing
    """

    def __init__(
        self,
        memory_size: int = 256,
        ttl_seconds: int = 3600,
        disk_path: Optional[str] = None,
    ):
        # L1: fast in-memory
        self.memory = TTLCache(maxsize=memory_size, ttl=ttl_seconds)

        # L2: persistent disk cache
        if disk_path is None:
            # Use temp directory on Windows or Linux
            disk_path = os.path.join(
                os.environ.get("TEMP", "/tmp"), "missioncart_cache"
            )
        try:
            self.disk = diskcache.Cache(disk_path)
        except Exception:
            self.disk = None

        self.hits_memory = 0
        self.hits_disk = 0
        self.misses = 0

    def _make_key(self, system_prompt: str, user_message: str) -> str:
        content = f"{system_prompt}|||{user_message}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, system_prompt: str, user_message: str) -> Optional[str]:
        key = self._make_key(system_prompt, user_message)

        # L1 check
        if key in self.memory:
            self.hits_memory += 1
            return self.memory[key]

        # L2 check
        if self.disk and key in self.disk:
            value = self.disk[key]
            self.memory[key] = value  # promote to L1
            self.hits_disk += 1
            return value

        self.misses += 1
        return None

    def set(self, system_prompt: str, user_message: str, response: str) -> None:
        key = self._make_key(system_prompt, user_message)
        self.memory[key] = response
        if self.disk:
            self.disk.set(key, response, expire=3600)

    def stats(self) -> dict:
        total = self.hits_memory + self.hits_disk + self.misses
        hit_rate = (
            (self.hits_memory + self.hits_disk) / total if total > 0 else 0
        )
        return {
            "hits_memory": self.hits_memory,
            "hits_disk": self.hits_disk,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1%}",
            "memory_size": len(self.memory),
        }


# Singleton
prompt_cache = PromptCache()
