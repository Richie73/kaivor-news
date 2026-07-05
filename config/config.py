"""
Kaivor Configuration Manager
"""

import json
from pathlib import Path


class ConfigManager:
    """Load JSON configuration files."""

    CONFIG_DIR = Path("config")

    def load(self, filename):
        path = self.CONFIG_DIR / filename

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, filename, data):
        path = self.CONFIG_DIR / filename

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
