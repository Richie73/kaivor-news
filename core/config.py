"""
Kaivor Configuration
"""

import json
from pathlib import Path


# Modules shown on the Kaivor startup screen
MODULES = [
    "Developer Dashboard",
    "AI News",
    "Technology News",
    "UK News",
    "World News",
    "Investment News",
    "Football News",
    "Android News",
    "Music News",
    "Search",
    "AI Daily Brief",
    "Diagnostics",
    "Developer Tools",
]


class Config:
    """Loads configuration from config/ai.json"""

    FILE = Path("config/ai.json")

    def __init__(self):
        self.data = json.loads(
            self.FILE.read_text(encoding="utf-8")
        )

    def get(self, key, default=None):
        return self.data.get(key, default)
