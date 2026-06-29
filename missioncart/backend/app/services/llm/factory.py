import os
from app.services.llm.base import BaseLLMClient


def get_llm_client():
    """Returns the correct LLM client based on env vars.

    Priority order:
    1. LLM_PROVIDER env var (explicit override)
    2. First available API key
    3. None (fallback mode — regex parser only)

    Set LLM_PROVIDER=groq|anthropic|bedrock
    """
    provider = os.environ.get("LLM_PROVIDER", "").lower().strip()

    # Explicit provider set
    if provider == "groq" and os.environ.get("GROQ_API_KEY"):
        from app.services.llm.providers import GroqClient

        print("LLM Provider: Groq")
        return GroqClient()

    if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        from app.services.llm.providers import AnthropicClient

        print("LLM Provider: Anthropic")
        return AnthropicClient()

    if provider == "bedrock" and os.environ.get("AWS_ACCESS_KEY_ID"):
        from app.services.llm.providers import BedrockClient

        print("LLM Provider: Amazon Bedrock")
        return BedrockClient()

    # Auto-detect from available keys
    if os.environ.get("GROQ_API_KEY"):
        from app.services.llm.providers import GroqClient

        print("LLM Provider: Groq (auto-detected)")
        return GroqClient()

    if os.environ.get("ANTHROPIC_API_KEY"):
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key and key != "your_key_here":
            from app.services.llm.providers import AnthropicClient

            print("LLM Provider: Anthropic (auto-detected)")
            return AnthropicClient()

    if os.environ.get("AWS_ACCESS_KEY_ID"):
        from app.services.llm.providers import BedrockClient

        print("LLM Provider: Bedrock (auto-detected)")
        return BedrockClient()

    # No provider available
    print("LLM Provider: NONE (fallback mode)")
    return None


# Singleton — instantiated once at startup
llm_client = get_llm_client()
