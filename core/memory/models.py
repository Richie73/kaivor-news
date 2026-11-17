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
        # FP112: rows carry eight columns now (importance, source,
        # tags added); tolerate the old five-column shape too.
        return cls(
            id=row[0],
            category=row[1],
            title=row[2],
            content=row[3],
            created_at=row[4],
            importance=row[5] if len(row) > 5 else 3,
            source=row[6] if len(row) > 6 else "manual",
            tags=row[7] if len(row) > 7 else "",
        )
