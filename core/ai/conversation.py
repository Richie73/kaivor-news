"""
Kaivor Conversation Manager
"""

import json
from pathlib import Path


class ConversationManager:

    FILE = Path("data/conversation.json")

    def __init__(self):

        self.FILE.parent.mkdir(exist_ok=True)

        if not self.FILE.exists():
            self.FILE.write_text("[]", encoding="utf-8")

        self._history = json.loads(
            self.FILE.read_text(encoding="utf-8")
        )

    def save(self):
        self.FILE.write_text(
            json.dumps(self._history, indent=4),
            encoding="utf-8",
        )

    def add_user(self, message: str):

        self._history.append(
            {
                "role": "user",
                "content": message,
            }
        )

        self.save()

    def add_assistant(self, message: str):

        self._history.append(
            {
                "role": "assistant",
                "content": message,
            }
        )

        self.save()

    def history(self):
        return list(self._history)

    def clear(self):
        self._history.clear()
        self.save()
