"""
Kaivor Knowledge Context Builder
"""

from core.knowledge.retriever import KnowledgeRetriever


class KnowledgeContextBuilder:
    """Builds AI context from retrieved documents."""

    def __init__(self):
        self.retriever = KnowledgeRetriever()

    def build(self, query, directory="knowledge", limit=5):
        """Return combined document text."""

        self.retriever.load(directory)

        documents = self.retriever.retrieve(
            query,
            limit=limit,
        )

        context = []

        for document in documents:

            context.append(
                f"# {document.title}\n\n{document.text}"
            )

        return "\n\n".join(context)
