"""
Kaivor Indexed Document
"""

from dataclasses import dataclass


@dataclass
class IndexedDocument:
    """Represents a searchable document."""

    title: str
    path: str
    text: str
