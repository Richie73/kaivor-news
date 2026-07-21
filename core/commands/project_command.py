"""
Kaivor Project Command
"""

from core.commands.base_command import BaseCommand
from core.projects import Projects


class ProjectCommand(BaseCommand):
    """Manage workspace projects."""

    name = "project"
    aliases = []
    help_text = "Manage projects."

    def __init__(self, workspace):
        self.projects = Projects(workspace)

    def execute(self, text=None):

        parts = text.split(maxsplit=2)

        if len(parts) == 1:
            return self.list()

        command = parts[1].lower()

        if command == "list":
            return self.list()

        if command == "current":

            current = self.projects.current()

            print()

            if current:
                print(f"Current project : {current}")
            else:
                print("No active project.")

            print()
            return

        if command == "switch":

            if len(parts) < 3:
                print("Usage: project switch <name>")
                return

            self.projects.switch(parts[2])

            print()
            print(f"Current project : {self.projects.current()}")
            print()
            return

        if command == "create":

            if len(parts) < 3:
                print("Usage: project create <name>")
                return

            project = self.projects.create(parts[2])

            print()
            print(f"Created: {project}")
            print()
            return

        self.help()

    def list(self):

        print()

        projects = self.projects.list()

        if not projects:
            print("No projects.")
        else:
            for project in projects:
                marker = "* " if project == self.projects.current() else "  "
                print(f"{marker}{project}")

        print()

    def help(self):

        print()
        print("project list")
        print("project current")
        print("project create <name>")
        print("project switch <name>")
        print()
