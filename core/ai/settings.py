"""
Kaivor AI Settings
"""

from enum import Enum

from config.config import ConfigManager


class AIMode(Enum):
    FREE = "free"
    ECONOMY = "economy"
    BALANCED = "balanced"
    PREMIUM = "premium"


class AISettings:

    def __init__(self):
        self.config = ConfigManager()

    def mode(self):
        cfg = self.config.load("ai.json")
        return AIMode(cfg["mode"])

    def default_task(self):
        cfg = self.config.load("ai.json")
        return cfg["default_task"]


_settings = AISettings()


def get_mode():
    return _settings.mode()


def get_default_task():
    return _settings.default_task()
