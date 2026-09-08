"""
Kaivor AI Base Classes
"""

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Base class for all AI providers."""

    @property
    @abstractmethod
    def name(self):
        """Provider name."""
        pass

    @abstractmethod
    def generate(self, prompt: str):
        """Generate a response."""
        pass
