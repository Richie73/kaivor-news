"""
Base AI Provider
"""

from abc import ABC, abstractmethod

from core.ai.request import AIRequest


class BaseProvider(ABC):
    """Base class for all AI providers."""

    name = "Unknown"

    enabled = True

    def configured(self):
        """Return True if the provider is configured."""
        return True

    @abstractmethod
    def generate(self, request: AIRequest):
        """Generate a response from an AIRequest."""
        raise NotImplementedError
