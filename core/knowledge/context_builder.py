"""
Kaivor Knowledge Context Builder
"""

from core.knowledge.retriever import KnowledgeRetriever


class KnowledgeContextBuilder:
    """Builds AI context from retrieved documents."""

    def __init__(self):
        self.retriever = KnowledgeRetriever()

    def build(
        self,
        query,
        directory="knowledge",
        limit=5,
    ):
        """Return context and source documents."""

        self.retriever.load(directory)

        documents = self.retriever.retrieve(
            query,
            limit=limit,
        )

        context = []
        sources = []

        for document in documents:

            title = getattr(
                document,
                "title",
                "Untitled",
            )

            sources.append(title)

            text = getattr(
                document,
                "text",
                "",
            )

            context.append(
                f"# {title}\n\n{text}"
            )

        return {
            "context": "\n\n".join(context),
            "sources": sources,
        }
