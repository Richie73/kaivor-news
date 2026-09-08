"""
Kaivor Command Registry
"""


class CommandRegistry:
    """Central registry for shell commands."""

    def __init__(self):
        self._commands = {}

    def register(self, name, handler, aliases=None):
        """
        Register a command.

        Parameters
        ----------
        name : str
            Primary command name.

        handler : callable
            Function or callable object.

        aliases : list[str] | tuple[str] | None
            Optional aliases.
        """

        aliases = aliases or []

        self._commands[name.lower()] = handler

        for alias in aliases:
            self._commands[alias.lower()] = handler

    def unregister(self, name):
        """Remove a registered command."""

        self._commands.pop(name.lower(), None)

    def exists(self, name):
        """Return True if a command exists."""

        return name.lower() in self._commands

    def execute(self, name, text):
        """Execute a command."""

        handler = self._commands.get(name.lower())

        if handler is None:
            return False

        handler(text)
        return True

    def names(self):
        """Return sorted unique command names."""

        return sorted(set(self._commands.keys()))

    def clear(self):
        """Remove all registered commands."""

        self._commands.clear()

    def count(self):
        """Return number of registered commands."""

        return len(self._commands)
