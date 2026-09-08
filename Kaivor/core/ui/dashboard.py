"""
Kaivor Session Dashboard
"""

import os
import time

from core.config import Config
from core.version import DISPLAY


class Dashboard:
    """Displays Kaivor startup information."""

    def __init__(self):
        self.started = time.time()
        self.config = Config()

    def _count(self, root, extension):
        total = 0

        if not os.path.isdir(root):
            return 0

        for _, _, files in os.walk(root):
            for filename in files:
                if filename.lower().endswith(extension):
                    total += 1

        return total

    def document_counts(self):
        root = "knowledge"

        txt = self._count(root, ".txt")
        docx = self._count(root, ".docx")
        pdf = self._count(root, ".pdf")

        return {
            "txt": txt,
            "docx": docx,
            "pdf": pdf,
            "total": txt + docx + pdf,
        }

    def provider(self):
        return self.config.get(
            "default_provider",
            "OpenRouter",
        )

    def model(self):
        return self.config.get(
            "default_model",
            "Unknown",
        )

    def uptime(self):
        seconds = int(time.time() - self.started)

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        return f"{hours:02}:{minutes:02}:{secs:02}"

    def health(self):
        return "HEALTHY"

    def show(self):
        docs = self.document_counts()

        print("=" * 60)
        print(DISPLAY)
        print("=" * 60)
        print()

        print("Session")
        print("-" * 60)

        print(f"Knowledge Library : {docs['total']} documents")
        print(f"TXT Files         : {docs['txt']}")
        print(f"DOCX Files        : {docs['docx']}")
        print(f"PDF Files         : {docs['pdf']}")
        print()
