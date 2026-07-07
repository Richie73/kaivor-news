"""
Kaivor Retrieval Service
"""

from core.knowledge.context_builder import (
    KnowledgeContextBuilder,
)


class RetrievalService:
    """Provides AI-ready knowledge context."""

    def __init__(self):
        self.builder = KnowledgeContextBuilder()

    def context(
        self,
        query,
        directory="knowledge",
        limit=5,
    ):
        """Return AI-ready context."""

        try:

            context = self.builder.build(
                query=query,
                directory=directory,
                limit=limit,
            )

            return context.strip()

        except Exception:

            return ""
