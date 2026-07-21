
"""
Kaivor Task Manager
"""

from pathlib import Path
import json


class Tasks:

    def __init__(self, workspace):
        self.root = workspace.current() / "tasks"
        self.root.mkdir(parents=True, exist_ok=True)

    def task_file(self, name):
        return self.root / f"{name}.json"

    def list(self):
        return sorted(
            file.stem
            for file in self.root.glob("*.json")
        )

    def create(self, name):

        path = self.task_file(name)

        data = {
            "name": name,
            "status": "todo",
            "priority": "normal",
            "completed": False,
        }

        path.write_text(
            json.dumps(data, indent=4),
            encoding="utf-8",
        )

        return path

    def exists(self, name):
        return self.task_file(name).exists()

    def read(self, name):

        with open(
            self.task_file(name),
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    def save(self, name, data):

        with open(
            self.task_file(name),
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
            )

    def complete(self, name):

        data = self.read(name)
        data["completed"] = True
        data["status"] = "completed"

        self.save(name, data)

    def delete(self, name):

        self.task_file(name).unlink(
            missing_ok=True,
        )