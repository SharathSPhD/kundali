from .base import InterpretationProvider
from .template_provider import TemplateProvider


def get_provider(name: str | None = None) -> InterpretationProvider:
    name = (name or "template").lower()
    if name == "template":
        return TemplateProvider()
    if name == "ollama":
        from .ollama_provider import OllamaProvider
        return OllamaProvider()
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    raise ValueError(f"unknown interpretation provider: {name}")
