"""
Kaivor Document Summariser
"""

from core.knowledge.document_loader import DocumentLoader


class DocumentSummariser:
    """Loads documents ready for AI summarisation."""

    def __init__(self):
        self.loader = DocumentLoader()

    def load(self, filename):
        """Return document text."""

        return self.loader.load(filename)

    def prepare(self, filename):
        """Prepare a document for summarisation."""

        text = self.load(filename)

        return (
            "Summarise the following document.\n\n"
            f"{text}"
        )
