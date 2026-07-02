"""
Kaivor AI Response
"""


class AIResponse:

    def __init__(
        self,
        success,
        content,
        raw=None,
        model=None,
        provider=None,
        elapsed=None,
        error=None,
    ):

        self.success = success
        self.content = content
        self.raw = raw
        self.model = model
        self.provider = provider
        self.elapsed = elapsed
        self.error = error

    def __str__(self):

        return self.content if self.success else f"ERROR: {self.error}"