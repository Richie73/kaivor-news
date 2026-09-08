"""
PDF Reader
"""

from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


class PDFReader:
    """Reads text from PDF files."""

    def read(self, filename):
        """Read a PDF and return its text."""

        if PdfReader is None:
            raise RuntimeError(
                "pypdf is not installed."
            )

        filename = Path(filename)

        reader = PdfReader(str(filename))

        text = []

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:
                text.append(page_text)

        return "\n".join(text)
