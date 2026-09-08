"""
Kaivor Knowledge Normalizer Module
Cleans, sanitizes, and chunks raw ingested text for storage and retrieval.
"""

import re

class KnowledgeNormalizer:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def clean_text(self, text: str) -> str:
        """Cleans whitespace, normalizes newlines, and strips unwanted artifacts."""
        if not text:
            return ""
        # Replace multiple spaces/newlines with clean formatting
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def chunk_text(self, text: str) -> list[str]:
        """Splits normalized text into manageable overlapping chunks for indexing."""
        cleaned = self.clean_text(text)
        if len(cleaned) <= self.chunk_size:
            return [cleaned]
        
        chunks = []
        start = 0
        while start < len(cleaned):
            end = start + self.chunk_size
            chunks.append(cleaned[start:end])
            start += (self.chunk_size - self.chunk_overlap)
        return chunks

    def normalize_document(self, raw_doc: dict) -> dict:
        """Processes a raw document dictionary into a normalized and chunked format."""
        content = raw_doc.get("content", "")
        cleaned_content = self.clean_text(content)
        chunks = self.chunk_text(cleaned_content)

        return {
            "title": raw_doc.get("title", "Untitled Document"),
            "category": raw_doc.get("category", "general"),
            "content": cleaned_content,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "length": len(cleaned_content)
        }
