"""
Kaivor Knowledge Search Service
"""

from core.knowledge.indexer import KnowledgeIndexer
from core.knowledge.config import KnowledgeConfig

class SearchService:
    """Search the knowledge base."""

    def __init__(self):
        self.indexer = KnowledgeIndexer()

    def search(
        self,
        query,
        directory=KnowledgeConfig.DIRECTORY,
        limit=KnowledgeConfig.SEARCH_LIMIT,
    ):
        """Return matching documents."""

        index = self.indexer.build(directory)

        results = index.search(query)

        return results[:limit]
