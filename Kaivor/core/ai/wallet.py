"""
Kaivor AI Wallet
"""

import json
from pathlib import Path


class AIWallet:

    FILE = Path("data/ai_usage.json")

    def __init__(self):
        if not self.FILE.exists():
            self.FILE.parent.mkdir(exist_ok=True)
            self.FILE.write_text("[]", encoding="utf-8")

    def history(self):
        return json.loads(
            self.FILE.read_text(encoding="utf-8")
        )

    def total_requests(self):
        return len(self.history())

    def providers(self):

        counts = {}

        for item in self.history():
            provider = item["provider"]
            counts[provider] = counts.get(provider, 0) + 1

        return counts

    def summary(self):
        return {
            "requests": self.total_requests(),
            "providers": self.providers(),
        }
