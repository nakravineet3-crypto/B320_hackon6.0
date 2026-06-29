import asyncio
import os
import time
from app.services.llm.base import BaseLLMClient, LLMResponse


# ── Groq ──────────────────────────────────────────────────


class GroqClient(BaseLLMClient):
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self):
        from groq import Groq

        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = os.environ.get("GROQ_MODEL", self.DEFAULT_MODEL)

    async def complete(
        self, system_prompt, user_message, max_tokens=500, temperature=0.1
    ) -> LLMResponse:
        start = time.perf_counter()
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                ),
                timeout=8.0,
            )
        except asyncio.TimeoutError:
            raise TimeoutError("LLM provider GroqClient timed out after 8s")
        latency = (time.perf_counter() - start) * 1000
        return LLMResponse(
            text=response.choices[0].message.content,
            provider="groq",
            model=self.model,
            latency_ms=latency,
            tokens_used=response.usage.total_tokens,
        )


# ── Anthropic ─────────────────────────────────────────────


class AnthropicClient(BaseLLMClient):
    DEFAULT_MODEL = "claude-haiku-4-5-20251001"

    def __init__(self):
        import anthropic

        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = os.environ.get("ANTHROPIC_MODEL", self.DEFAULT_MODEL)

    async def complete(
        self, system_prompt, user_message, max_tokens=500, temperature=0.1
    ) -> LLMResponse:
        start = time.perf_counter()
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.messages.create,
                    model=self.model,
                    max_tokens=max_tokens,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[{"role": "user", "content": user_message}],
                ),
                timeout=8.0,
            )
        except asyncio.TimeoutError:
            raise TimeoutError("LLM provider AnthropicClient timed out after 8s")
        latency = (time.perf_counter() - start) * 1000
        cache_hit = hasattr(response, "usage") and getattr(
            response.usage, "cache_read_input_tokens", 0
        ) > 0
        return LLMResponse(
            text=response.content[0].text,
            provider="anthropic",
            model=self.model,
            latency_ms=latency,
            cached=cache_hit,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
        )


# ── Amazon Bedrock ────────────────────────────────────────


class BedrockClient(BaseLLMClient):
    DEFAULT_MODEL = "anthropic.claude-haiku-4-5-20251001-v1:0"

    def __init__(self):
        import boto3
        import json

        self.json = json
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-south-1"),
        )
        self.model = os.environ.get("BEDROCK_MODEL_ID", self.DEFAULT_MODEL)

    async def complete(
        self, system_prompt, user_message, max_tokens=500, temperature=0.1
    ) -> LLMResponse:
        start = time.perf_counter()
        body = self.json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            }
        )
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.invoke_model,
                    modelId=self.model,
                    body=body,
                ),
                timeout=8.0,
            )
        except asyncio.TimeoutError:
            raise TimeoutError("LLM provider BedrockClient timed out after 8s")
        result = self.json.loads(response["body"].read())
        latency = (time.perf_counter() - start) * 1000
        return LLMResponse(
            text=result["content"][0]["text"],
            provider="bedrock",
            model=self.model,
            latency_ms=latency,
        )
