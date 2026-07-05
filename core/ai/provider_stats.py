"""
Kaivor Provider Statistics
"""

import json
from pathlib import Path


class ProviderStats:
    """Tracks provider performance."""

    FILE = Path("data/provider_stats.json")

    def __init__(self):

        self.FILE.parent.mkdir(exist_ok=True)

        if self.FILE.exists():
            self.stats = json.loads(
                self.FILE.read_text(encoding="utf-8")
            )
        else:
            self.stats = {}

    def save(self):

        self.FILE.write_text(
            json.dumps(self.stats, indent=4),
            encoding="utf-8",
        )

    def record_success(self, provider, latency):

        stat = self.stats.setdefault(
            provider,
            {
                "success": 0,
                "failure": 0,
                "latency": [],
            },
        )

        stat["success"] += 1
        stat["latency"].append(latency)

        self.save()

    def record_failure(self, provider):

        stat = self.stats.setdefault(
            provider,
            {
                "success": 0,
                "failure": 0,
                "latency": [],
            },
        )

        stat["failure"] += 1

        self.save()

    def summary(self):

        result = {}

        for provider, stat in self.stats.items():

            average = 0

            if stat["latency"]:
                average = (
                    sum(stat["latency"])
                    / len(stat["latency"])
                )

            result[provider] = {
                "success": stat["success"],
                "failure": stat["failure"],
                "average_latency": round(average, 2),
            }

        return result
