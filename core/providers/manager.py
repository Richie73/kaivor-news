"""
Kaivor Provider Manager — FP107: one working provider layer.

Registers the providers, orders them by the priority in
config/providers.json, and runs a request down the fallback
chain until one succeeds. This is the single entry point the
live app's AI callers use (FP108 wires them to it).
"""

from config.config import ConfigManager

from core.ai.request import AIRequest
from core.providers.base import ProviderError
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

    def generate_with_fallback(self, request: AIRequest, model=None, chain=None):
        """Run a request down the fallback chain; return (name, text).

        Unconfigured providers are skipped, failed providers are
        tried next, and ProviderError is raised only when every
        provider in the chain has failed (with each failure named).
        The model, when given, applies to every provider tried.
        """
        names = list(chain) if chain is not None else self.fallback_chain()
        failures = []
        for name in names:
            provider = self.get(name)
            if provider is None:
                failures.append(f"{name}: not registered")
                continue
            try:
                if not provider.configured():
                    failures.append(f"{name}: not configured")
                    continue
                return name, provider.generate(request, model=model)
            except Exception as exc:  # noqa: BLE001 — one provider's failure must not stop the chain
                failures.append(f"{name}: {exc}")
        raise ProviderError(
            "All providers failed: " + "; ".join(failures) if failures else "No providers in chain."
        )

    def health(self):
        """Return provider configuration status."""

        status = {}

        for name, provider in self.providers.items():

            try:
                status[name] = provider.configured()

            except Exception:
                status[name] = False

        return status



