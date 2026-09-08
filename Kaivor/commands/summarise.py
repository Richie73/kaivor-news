"""
Kaivor Summarise Command
"""

from core.knowledge.document_summariser import (
    DocumentSummariser,
)


def run(filename):
    """Prepare a document for AI summarisation."""

    summariser = DocumentSummariser()

    prompt = summariser.prepare(filename)

    print()
    print("=" * 60)
    print("Document prepared for AI summarisation")
    print("=" * 60)
    print()

    print(prompt)
