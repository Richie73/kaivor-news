"""
Kaivor Notes Manager
"""

from pathlib import Path


class Notes:
    """Manage workspace notes."""

    def __init__(self, workspace):
        self.workspace = workspace

    def root(self):
        return self.workspace.current() / "notes"

    def list(self):
        root = self.root()

        if not root.exists():
            return []

        return sorted(
            item.stem
            for item in root.glob("*.md")
            if item.is_file()
        )

    def add(self, title):

        filename = f"{title}.md"
        note = self.root() / filename

        if note.exists():
            return note

        note.write_text(
            f"# {title}\n\n",
            encoding="utf-8",
        )

        return note

    def open(self, title):

        note = self.root() / f"{title}.md"

        if not note.exists():
            return None

        return note.read_text(
            encoding="utf-8",
        )

    def delete(self, title):

        note = self.root() / f"{title}.md"

        if note.exists():
            note.unlink()
            return True

        return False
