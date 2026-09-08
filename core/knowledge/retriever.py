"""
Kaivor Knowledge Retriever
"""

from core.knowledge.store import KnowledgeStore


class KnowledgeRetriever:
    """Retrieves relevant documents."""

    def __init__(self):
        self.store = KnowledgeStore()

    def load(self, directory="knowledge"):
        """Load all knowledge documents."""

        self.store.load_directory(directory)

    def retrieve(self, query, limit=5):
        """Return the most relevant documents."""

        results = self.store.search(query)

        return results[:limit]
