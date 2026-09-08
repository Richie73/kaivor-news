"""
Kaivor Knowledge Ingestion Module
Handles raw document reading, file parsing, and content extraction.
"""

import os

class KnowledgeIngestion:
    def __init__(self):
        pass

    def read_file(self, filepath: str) -> str:
        """Reads raw text or markdown content from a local file path."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Knowledge file not found: {filepath}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def process_raw_text(self, text: str, title: str = "Untitled Document", category: str = "general") -> dict:
        """Wraps raw ingested text into a structured dictionary ready for normalization."""
        return {
            "title": title,
            "category": category,
            "content": text.strip(),
            "length": len(text)
        }
