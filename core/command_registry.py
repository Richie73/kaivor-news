"""
Kaivor Command Registry
"""


class CommandRegistry:
    """Registry for shell commands."""

    def __init__(self):
        self.commands = {}

    def register(self, name, handler):
        self.commands[name.lower()] = handler

    def dispatch(self, text):
        if not text:
            return False

        command = text.split()[0].lower()

        handler = self.commands.get(command)

        if handler is None:
            return False

        handler(text)

        return True

    def names(self):
        return sorted(self.commands.keys())
