"""
Kaivor RAG Service
"""

from core.knowledge.retrieval_service import RetrievalService


class RAGService:
    """Provides AI-ready knowledge context."""

    def __init__(self):
        self.retrieval = RetrievalService()

    def context(
        self,
        question,
        directory="knowledge",
        limit=5,
    ):
        """Build context for AI."""

        passages = self.retrieval.knowledge(
            query=question,
            directory=directory,
            limit=limit,
        )

        if not passages:
            return {
                "context": "",
                "sources": [],
            }

        context_parts = []
        sources = []

        for item in passages:

            context_parts.append(
                f"[{item['title']}]\n{item['excerpt']}"
            )

            sources.append(
                {
                    "title": item["title"],
                    "path": item["path"],
                }
            )

        return {
            "context": "\n\n".join(context_parts),
            "sources": sources,
        }
