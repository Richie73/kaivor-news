"""
Kaivor Command Registry
"""


class CommandRegistry:
    """Registers shell commands."""

    def __init__(self):
        self.commands = {}

    def register(self, command):

        self.commands[command.name.lower()] = command

        for alias in getattr(command, "aliases", []):
            self.commands[alias.lower()] = command

    def exists(self, name):
        return name.lower() in self.commands

    def execute(self, text):

        if not text:
            return False

        command_name = text.split()[0].lower()

        command = self.commands.get(command_name)

        if command is None:
            return False

        command.execute(text)

        return True

    def names(self):

        names = []

        for command in self.commands.values():

            if command.name not in names:
                names.append(command.name)

        return sorted(names)
