"""Application service and validation for Kaivor Reading."""

from pathlib import Path
import math

from reading.models import BOOK_FORMATS, READING_STATUSES, Book, ReadingNote, ReadingProgress
from reading.repository import ReadingRepository


class ReadingValidationError(ValueError):
    """Raised when a reading record violates domain rules."""


class ReadingService:
    def __init__(self, db_path: str | Path | None = None, repository: ReadingRepository | None = None):
        self.repository = repository or ReadingRepository(db_path)

    def add_book(self, title: str, author: str | None = None, book_format: str = "other",
                 status: str = "want_to_read", provider: str | None = None,
                 provider_item_id: str | None = None, description: str | None = None) -> Book:
        title = title.strip() if title else ""
        if not title:
            raise ReadingValidationError("Book title is required.")
        if book_format not in BOOK_FORMATS:
            raise ReadingValidationError(f"Format must be one of: {', '.join(BOOK_FORMATS)}")
        if status not in READING_STATUSES:
            raise ReadingValidationError(f"Status must be one of: {', '.join(READING_STATUSES)}")
        return self.repository.add_book(title, author.strip() if author else None, book_format,
                                        status, provider, provider_item_id, description)

    def update_status(self, book_id: int, status: str) -> Book | None:
        if status not in READING_STATUSES:
            raise ReadingValidationError(f"Status must be one of: {', '.join(READING_STATUSES)}")
        return self.repository.update_book(book_id, status=status)

    def add_note(self, book_id: int, note: str, page_reference: str | None = None) -> ReadingNote:
        if not note or not note.strip():
            raise ReadingValidationError("Note cannot be empty.")
        if not self.repository.get_book(book_id):
            raise ReadingValidationError(f"Book {book_id} does not exist.")
        return self.repository.add_note(book_id, note.strip(), page_reference)

    def record_progress(self, book_id: int, value: float, unit: str = "percent") -> ReadingProgress:
        if not self.repository.get_book(book_id):
            raise ReadingValidationError(f"Book {book_id} does not exist.")
        if not math.isfinite(float(value)):
            raise ReadingValidationError("Progress must be a finite number.")
        if value < 0:
            raise ReadingValidationError("Progress cannot be negative.")
        if unit not in ("percent", "page", "minute", "chapter"):
            raise ReadingValidationError("Unit must be percent, page, minute, or chapter.")
        if unit == "percent" and value > 100:
            raise ReadingValidationError("Percentage progress cannot exceed 100.")
        return self.repository.record_progress(book_id, value, unit)


    def delete_book(self, book_id: int) -> bool:
        return self.repository.delete_book(book_id)

    def dashboard(self) -> dict:
        return self.repository.summary()
