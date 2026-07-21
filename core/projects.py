"""
Kaivor Project Manager
"""

from pathlib import Path


class Projects:

    def __init__(self, workspace):
        self.root = workspace.current() / "projects"
        self.root.mkdir(parents=True, exist_ok=True)
        self.active_file = self.root / ".active"

    def list(self):
        return sorted(
            item.name
            for item in self.root.iterdir()
            if item.is_dir()
        )

    def create(self, name):
        project = self.root / name
        project.mkdir(parents=True, exist_ok=True)

        if not self.active_file.exists():
            self.switch(name)

        return project

    def exists(self, name):
        return (self.root / name).exists()

    def switch(self, name):
        if not self.exists(name):
            self.create(name)

        self.active_file.write_text(
            name,
            encoding="utf-8",
        )

    def current(self):
        if not self.active_file.exists():
            return None

        return self.active_file.read_text(
            encoding="utf-8",
        ).strip()
