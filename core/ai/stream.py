"""
Kaivor Streaming Manager
"""

from core.config import Config


class StreamManager:
    """Handles streamed AI responses."""

    def __init__(self):
        self.config = Config()

    def enabled(self):
        """Return whether streaming is enabled."""

        return self.config.get(
            "streaming",
            True,
        )

    def enabled_for_provider(self, provider):
        """Return True if this provider supports streaming."""

        return (
            self.enabled()
            and hasattr(provider, "stream_generate")
        )

    def stream(self, provider, request):
        """Yield streamed response chunks."""

        if not self.enabled_for_provider(provider):
            raise NotImplementedError(
                "Streaming not supported."
            )

        yield from provider.stream_generate(request)
