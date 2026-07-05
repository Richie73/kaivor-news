"""
Kaivor Provider Manager
"""

from config.config import ConfigManager

from core.providers.openrouter import OpenRouterProvider
from core.providers.openai import OpenAIProvider
from core.providers.anthropic import AnthropicProvider
from core.providers.google import GoogleProvider
from core.providers.ollama import OllamaProvider
from core.providers.deepseek import DeepSeekProvider

class ProviderManager:
    """Central registry for AI providers."""

    def __init__(self):
        self.providers = {}
        self.config = ConfigManager()

        self.register(OpenRouterProvider())
        self.register(DeepSeekProvider())
        self.register(OpenAIProvider())
        self.register(AnthropicProvider())
        self.register(GoogleProvider())
        self.register(OllamaProvider())

    def register(self, provider):
        self.providers[provider.name] = provider

    def get(self, name):
        return self.providers.get(name)

    def list(self):
        return sorted(self.providers.keys())

    def provider_config(self):
        return self.config.load("providers.json")["providers"]

    def enabled(self):
        cfg = self.provider_config()

        return [
            name
            for name, settings in cfg.items()
            if settings.get("enabled", False)
        ]

    def disabled(self):
        cfg = self.provider_config()

        return [
            name
            for name, settings in cfg.items()
            if not settings.get("enabled", False)
        ]

    def ordered(self):
        cfg = self.provider_config()

        return sorted(
            self.enabled(),
            key=lambda provider: cfg[provider]["priority"]
        )

    def primary(self):
        providers = self.ordered()

        if not providers:
            raise RuntimeError("No providers enabled.")

        return providers[0]

    def fallback_chain(self):
        """Return providers in failover order."""
        return self.ordered()

    def next_provider(self, current):
        """Return the next available provider."""

        chain = self.fallback_chain()

        if current not in chain:
            return None

        index = chain.index(current)

        if index + 1 >= len(chain):
            return None

        return chain[index + 1]
