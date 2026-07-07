"""
Knowledge Store
"""

from pathlib import Path

from core.knowledge.document import KnowledgeDocument


class KnowledgeStore:
    """Stores knowledge documents."""

    def __init__(self):
        self.documents = []

    def add(self, document):
        """Add a document to the store."""
        self.documents.append(document)

    def all(self):
        """Return every stored document."""
        return self.documents

    def load_directory(self, directory):
        """Load all text files from a directory."""

        directory = Path(directory)

        if not directory.exists():
            return

        for path in directory.rglob("*"):

            if not path.is_file():
                continue

            try:
                text = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

            except Exception:
                continue

            self.add(
                KnowledgeDocument(
                    path=path,
                    title=path.name,
                    text=text,
                    metadata={},
                )
            )

    def search(self, query):
        """Return documents containing the query."""

        query = query.lower()

        results = []

        for document in self.documents:

            if (
                query in document.title.lower()
                or query in document.text.lower()
            ):
                results.append(document)

        return results
