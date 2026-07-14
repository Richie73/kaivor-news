"""
Kaivor Base Command
"""


class BaseCommand:
    """Base class for all shell commands."""

    name = ""
    aliases = []
    help_text = ""

    def __call__(self, text=None):
        return self.execute(text)

    def execute(self, text=None):
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement execute()."
        )
