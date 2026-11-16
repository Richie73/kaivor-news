"""
Base AI Provider — FP107: the single provider interface.

Every provider in core/providers implements this: a name, a
configured() check, and generate(request, model=None) returning
the reply text. Keys come from environment variables at call
time, the same way the live app reads them — never from
config/secrets.py (legacy) and never baked into the provider.
"""

from abc import ABC, abstractmethod

from core.ai.request import AIRequest


class ProviderError(Exception):
    """A provider call failed (unconfigured, HTTP error, bad response)."""


class BaseProvider(ABC):
    """Base class for all AI providers."""

    name = "Unknown"

    enabled = True

    # The model used when the caller does not pick one.
    default_model = None

    # Environment variable holding this provider's API key.
    env_var = None

    def api_key(self):
        """The provider's API key from the environment, or None."""
        import os

        if not self.env_var:
            return None
        return os.environ.get(self.env_var) or None

    def configured(self):
        """Return True when the provider has a key to call with."""
        return bool(self.api_key())

    @abstractmethod
    def generate(self, request: AIRequest, model=None):
        """Generate a reply from an AIRequest; returns the text."""
        raise NotImplementedError
