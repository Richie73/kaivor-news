"""
Kaivor Memory Models
"""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Memory:
    id: Optional[int]
    category: str
    title: str
    content: str
    created_at: Optional[str] = None
    importance: int = 3
    source: str = "manual"
    tags: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row[0],
            category=row[1],
            title=row[2],
            content=row[3],
            created_at=row[4],
        )
