"""
Kaivor Workspace Manager
"""

from pathlib import Path


class Workspace:

    ROOT = Path("workspace")
    ACTIVE = ROOT / ".active"

    DIRECTORIES = (
        "agents",
        "chats",
        "documents",
        "exports",
        "knowledge",
        "notes",
        "projects",
        "tasks",
    )

    def initialise(self):

        self.ROOT.mkdir(exist_ok=True)

        if not self.ACTIVE.exists():
            self.create("Default")
            self.switch("Default")
        else:
            self.create(self.name())

    def create(self, name):

        workspace = self.ROOT / name

        workspace.mkdir(parents=True, exist_ok=True)

        for directory in self.DIRECTORIES:
            (workspace / directory).mkdir(
                parents=True,
                exist_ok=True,
            )

    def list(self):

        if not self.ROOT.exists():
            return []

        return sorted(
            item.name
            for item in self.ROOT.iterdir()
            if item.is_dir()
        )

    def switch(self, name):

        self.create(name)

        self.ACTIVE.write_text(
            name,
            encoding="utf-8",
        )

    def name(self):

        if not self.ACTIVE.exists():
            return "Default"

        return self.ACTIVE.read_text(
            encoding="utf-8",
        ).strip()

    def current(self):

        return self.ROOT / self.name()
