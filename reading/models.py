"""Typed domain models for the Kaivor Reading module."""

from dataclasses import dataclass
from typing import Optional


READING_STATUSES = ("want_to_read", "reading", "paused", "finished", "abandoned")
BOOK_FORMATS = ("ebook", "audiobook", "print", "magazine", "newspaper", "other")


@dataclass(frozen=True, slots=True)
class Book:
    id: int
    title: str
    author: Optional[str]
    book_format: str
    status: str
    provider: Optional[str]
    provider_item_id: Optional[str]
    description: Optional[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ReadingNote:
    id: int
    book_id: int
    note: str
    page_reference: Optional[str]
    created_at: str


@dataclass(frozen=True, slots=True)
class ReadingProgress:
    id: int
    book_id: int
    progress_value: float
    progress_unit: str
    recorded_at: str
