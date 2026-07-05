"""
Kaivor AI Router
"""

from core.ai.resource_manager import AIResourceManager
from core.providers.manager import ProviderManager


class AIRouter:
    """Central AI routing engine."""

    def __init__(self):
        self.resources = AIResourceManager()
        self.providers = ProviderManager()

    def current_mode(self):
        return self.resources.get_mode()

    def selected_model(self):
        return self.resources.select_model()

    def available_providers(self):
        return self.providers.enabled()

    def primary_provider(self):
        enabled = self.providers.enabled()

        if not enabled:
            raise RuntimeError("No AI providers are enabled.")

        return enabled[0]
