"""
DOCX Reader
"""

from pathlib import Path

try:
    from docx import Document
except ImportError:
    Document = None


class DOCXReader:
    """Reads text from Microsoft Word documents."""

    def read(self, filename):
        """Return text from a DOCX file."""

        if Document is None:
            raise RuntimeError(
                "python-docx is not installed."
            )

        filename = Path(filename)

        document = Document(str(filename))

        paragraphs = []

        for paragraph in document.paragraphs:

            if paragraph.text.strip():

                paragraphs.append(
                    paragraph.text
                )

        return "\n".join(paragraphs)
