from .base import InterpretationProvider
from .template_provider import TemplateProvider


def get_provider(name: str | None = None, **kwargs) -> InterpretationProvider:
    """`kwargs` (api_key, base_url, model, ...) are BYOK/gateway overrides —
    every non-template provider accepts them and falls back to its own env
    vars when omitted, so the same factory serves both the app-default env
    configuration and per-request tier/BYOK resolution (see gateway.py)."""
    name = (name or "template").lower()
    if name == "template":
        return TemplateProvider()
    if name == "ollama":
        from .ollama_provider import OllamaProvider
        return OllamaProvider(**kwargs)
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(**kwargs)
    if name == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(**kwargs)
    if name == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider(**kwargs)
    raise ValueError(f"unknown interpretation provider: {name}")
