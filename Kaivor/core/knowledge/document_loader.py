"""
Kaivor Document Loader
"""

from pathlib import Path

from core.knowledge.docx_reader import DOCXReader
from core.knowledge.pdf_reader import PDFReader


class DocumentLoader:
    """Loads supported document types."""

    SUPPORTED_TYPES = {
        ".txt",
        ".pdf",
        ".docx",
    }

    def __init__(self):
        self.pdf = PDFReader()
        self.docx = DOCXReader()

    def supports(self, filename):
        """Return True if the file type is supported."""

        filename = Path(filename)

        return (
            filename.suffix.lower()
            in self.SUPPORTED_TYPES
        )

    def load(self, filename):
        """Return plain text from a supported document."""

        filename = Path(filename)

        suffix = filename.suffix.lower()

        if not self.supports(filename):
            raise ValueError(
                f"Unsupported document type: {suffix}"
            )

        if suffix == ".pdf":
            return self.pdf.read(filename)

        if suffix == ".docx":
            return self.docx.read(filename)

        return filename.read_text(
            encoding="utf-8",
            errors="ignore",
        )
