"""
Kaivor Document Index
"""

from core.knowledge.passage_ranker import PassageRanker


class DocumentIndex:
    """Simple keyword document index."""

    def __init__(self):
        self.documents = []

    def clear(self):
        self.documents.clear()

    def add(self, document):
        self.documents.append(document)

    def search(self, query):
        """Search indexed documents."""

        query_lower = query.lower()

        results = []

        for document in self.documents:

            text_lower = document.text.lower()

            if query_lower not in text_lower:

                # If every individual keyword is absent, skip document.
                keywords = [
                    word
                    for word in query_lower.split()
                    if len(word) > 2
                ]

                if not any(word in text_lower for word in keywords):
                    continue

            excerpt = PassageRanker.best_passage(
                document.text,
                query,
            )

            results.append(
                {
                    "document": document,
                    "excerpt": excerpt,
                }
            )

        return results
