"""
Knowledge Document
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class KnowledgeDocument:
    """Represents one document in Kaivor's knowledge base."""

    path: Path
    title: str
    text: str
    metadata: dict
