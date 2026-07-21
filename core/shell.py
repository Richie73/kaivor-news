"""
Kaivor Interactive Shell
"""

import os

from core.ai.engine import AIEngine
from core.ai.tasks import AITasks
from core.ui.dashboard import Dashboard
from core.universal_search import UniversalSearch
from core.workspace import Workspace
from core.command_registry import CommandRegistry
from core.commands.help_command import HelpCommand
from core.commands.note_command import NoteCommand
from core.commands.project_command import ProjectCommand
from core.commands.task_command import TaskCommand

class InteractiveShell:
    """Interactive command shell."""

    def __init__(self):
        self.engine = AIEngine()
        self.dashboard = Dashboard()
        self.workspace = Workspace()
        self.search = UniversalSearch()
        self.workspace.initialise()
        self.help_command = HelpCommand()
        self.registry = CommandRegistry()

        self.registry.register(
            "help",
            self.help_command.execute,
)

        self.registry.register(
            "note",
            NoteCommand(self.workspace).execute,
)

        self.registry.register(
            "task",
            TaskCommand(self.workspace).execute,
)
        self.registry.register(
            "project",
            ProjectCommand(self.workspace).execute,
)

    def banner(self):

        print()
        self.dashboard.show()
        print(f"Workspace         : {self.workspace.name()}")
        print()
        print("Interactive AI")
        print()
        print("Type help for commands.")
        print()

    def help(self):
        self.help_command()

    def clear(self):
        os.system("clear")

    def show_sources(self):

        sources = getattr(self.engine, "last_sources", [])

        if not sources:
            return

        print()
        print("-" * 60)
        print("Sources")
        print("-" * 60)

        for source in sources:

            if isinstance(source, dict):
                title = source.get("title", "Unknown")
                path = source.get("path", "")
            else:
                title = getattr(source, "title", "Unknown")
                path = getattr(source, "path", "")

            print(f"• {title}")

            if path:
                print(f"  {path}")

        print()

    def handle_workspace(self, text):

        parts = text.split()

        if len(parts) == 1:
            print()
            print(f"Current workspace : {self.workspace.name()}")
            print()
            return True

        command = parts[1].lower()

        if command == "list":

            print()
            print("Available Workspaces")
            print("-" * 60)

            for name in self.workspace.list():
                marker = "* " if name == self.workspace.name() else "  "
                print(f"{marker}{name}")

            print()
            return True

        if command == "current":

            print()
            print(f"Current workspace : {self.workspace.name()}")
            print()
            return True

        if command == "create":

            if len(parts) < 3:
                print("Usage: workspace create <name>")
                return True

            name = " ".join(parts[2:])

            self.workspace.create(name)

            print()
            print(f'Workspace "{name}" created.')
            print()

            return True

        if command == "switch":

            if len(parts) < 3:
                print("Usage: workspace switch <name>")
                return True

            name = " ".join(parts[2:])

            self.workspace.switch(name)

            print()
            print(f'Current workspace : {name}')
            print()

            return True

        print("Unknown workspace command.")
        return True

    def handle_search(self, text):

        parts = text.split(maxsplit=1)

        if len(parts) != 2:

            print()
            print("Usage: search <text>")
            print()

            return

        results = self.search.search(
            self.workspace.current(),
            parts[1],
        )

        print()

        if not results:

            print("No results found.")
            print()

            return

        print(f"Found {len(results)} result(s)")
        print("-" * 60)

        for result in results:

            print(f"[{result['type']}] {result['name']}")
            print(result["path"])
            print()

    def ask(self, question):

        try:

            answer = self.engine.ask(
                AITasks.CHAT,
                question,
            )

            print()
            print(answer)

            self.show_sources()

        except KeyboardInterrupt:

            print()
            print("Request cancelled.")
            print()

        except Exception as exc:

            print()
            print(f"Error: {exc}")
            print()

    def run(self):

        self.banner()

        while True:

            try:
                text = input("> ").strip()

            except (KeyboardInterrupt, EOFError):

                print()
                print("Goodbye.")
                print()

                return

            if not text:
                continue

            lower = text.lower()

            if self.registry.dispatch(text):
                continue

            if lower == "clear":
                self.clear()
                self.banner()
                continue

            if lower in ("exit", "quit"):
                print()
                print("Goodbye.")
                print()
                return

            if lower.startswith("workspace"):
                self.handle_workspace(text)
                continue

            if lower.startswith("search"):
                self.handle_search(text)
                continue

            self.ask(text)
