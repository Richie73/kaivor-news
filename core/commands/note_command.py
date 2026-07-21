"""
Kaivor Note Command
"""

from core.commands.base_command import BaseCommand
from core.notes import Notes


class NoteCommand(BaseCommand):
    """Manage workspace notes."""

    name = "note"
    aliases = []
    help_text = "Manage notes."

    def __init__(self, workspace):
        self.notes = Notes(workspace)

    def execute(self, text=None):

        parts = text.split(maxsplit=2)

        if len(parts) < 2:
            return self.show_help()

        command = parts[1].lower()

        if command == "list":
            print()

            notes = self.notes.list()

            if not notes:
                print("No notes.")
            else:
                for note in notes:
                    print(note)

            print()
            return

        if command == "add":

            if len(parts) < 3:
                print("Usage: note add <title>")
                return

            note = self.notes.add(parts[2])

            print()
            print(f"Created: {note}")
            print()
            return

        if command == "open":

            if len(parts) < 3:
                print("Usage: note open <title>")
                return

            content = self.notes.open(parts[2])

            if content is None:
                print("Note not found.")
                return

            print()
            print(content)
            print()
            return

        if command == "delete":

            if len(parts) < 3:
                print("Usage: note delete <title>")
                return

            if self.notes.delete(parts[2]):
                print("Deleted.")
            else:
                print("Note not found.")

            return

        self.show_help()

    def show_help(self):

        print()
        print("note add <title>")
        print("note list")
        print("note open <title>")
        print("note delete <title>")
        print()
