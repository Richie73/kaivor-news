"""
Kaivor Knowledge Service Module
Coordinates ingestion, normalization, and local SQLite storage for the knowledge pipeline.
"""

from core.knowledge.ingestion import KnowledgeIngestion
from core.knowledge.normalizer import KnowledgeNormalizer
from core.knowledge.store import KnowledgeStore

class KnowledgeService:
    def __init__(self, db_path: str = "database/knowledge.db"):
        self.ingestion = KnowledgeIngestion()
        self.normalizer = KnowledgeNormalizer()
        self.store = KnowledgeStore(db_path=db_path)

    def ingest_and_store_file(self, filepath: str, category: str = "general") -> dict:
        """Ingests a file, normalizes and chunks its content, and persists it to the store."""
        # 1. Read raw file
        raw_text = self.ingestion.read_file(filepath)
        
        # Extract title from filename or fallback
        import os
        filename = os.path.basename(filepath)
        title = os.path.splitext(filename)[0].replace("_", " ").title()

        # 2. Wrap into raw document dictionary
        raw_doc = {
            "title": title,
            "category": category,
            "content": raw_text
        }

        # 3. Normalize and chunk document
        normalized_doc = self.normalizer.normalize_document(raw_doc)

        # 4. Store chunks in SQLite
        inserted_chunks = self.store.store_document(normalized_doc)

        return {
            "title": title,
            "category": category,
            "chunks_stored": inserted_chunks,
            "total_length": normalized_doc["length"]
        }

    def search_knowledge(self, query: str, limit: int = 5) -> list[dict]:
        """Searches stored knowledge chunks for a given query."""
        return self.store.search_chunks(query, limit=limit)
