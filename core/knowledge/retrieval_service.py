"""
Kaivor Retrieval Service
"""

from core.knowledge.retriever import KnowledgeRetriever


class RetrievalService:
    """Central knowledge retrieval service."""

    def __init__(self):
        self.retriever = KnowledgeRetriever()

    def knowledge(
        self,
        query,
        directory="knowledge",
        limit=5,
    ):
        """Retrieve knowledge passages."""

        return self.retriever.retrieve(
            query=query,
            directory=directory,
            limit=limit,
        )
