"""
Kaivor Provider Discovery
"""

from core.ai.registry import MODELS


class ProviderDiscovery:
    """Discover available AI models."""

    def get_all_models(self):
        return MODELS

    def get_free_models(self):
        return {
            name: model
            for name, model in MODELS.items()
            if model["free"]
        }

    def get_paid_models(self):
        return {
            name: model
            for name, model in MODELS.items()
            if not model["free"]
        }
