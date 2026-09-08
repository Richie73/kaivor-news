"""
Kaivor RAG Service
"""

from core.knowledge.retrieval_service import RetrievalService


class RAGService:
    """Provides knowledge context for AI queries."""

    def __init__(self):
        self.retrieval = RetrievalService()

    def context(
        self,
        question,
        directory="knowledge",
        limit=5,
    ):
        """Return knowledge context."""

        return self.retrieval.context(
            query=question,
            directory=directory,
            limit=limit,
        )
