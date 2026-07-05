"""
Kaivor AI Usage Logger
"""

from datetime import datetime
import json
from pathlib import Path


class UsageLogger:

    FILE = Path("data/ai_usage.json")

    def __init__(self):
        self.FILE.parent.mkdir(exist_ok=True)

        if not self.FILE.exists():
            self.FILE.write_text("[]", encoding="utf-8")

    def log(self, provider, model, prompt, response):

        usage = json.loads(
            self.FILE.read_text(encoding="utf-8")
        )

        usage.append(
            {
                "timestamp": datetime.now().isoformat(),
                "provider": provider,
                "model": model,
                "prompt_length": len(prompt),
                "response_length": len(response),
            }
        )

        self.FILE.write_text(
            json.dumps(usage, indent=4),
            encoding="utf-8",
        )
