"""Regression tests for FP041 Reading Foundation."""

import pytest

from reading.models import READING_STATUSES
from reading.service import ReadingService, ReadingValidationError



@pytest.fixture
def service(tmp_path):
    return ReadingService(tmp_path / "reading-test.db")


def test_add_and_retrieve_book(service):
    book = service.add_book("  Dune  ", "Frank Herbert", "ebook")
    loaded = service.repository.get_book(book.id)
    assert loaded.title == "Dune"
    assert loaded.author == "Frank Herbert"
    assert loaded.status == "want_to_read"


def test_rejects_empty_title(service):
    with pytest.raises(ReadingValidationError, match="title is required"):
        service.add_book("  ")


def test_rejects_invalid_format_and_status(service):
    with pytest.raises(ReadingValidationError, match="Format"):
        service.add_book("Book", book_format="cassette")
    with pytest.raises(ReadingValidationError, match="Status"):
        service.add_book("Book", status="maybe")


def test_status_transition_and_filter(service):
    book = service.add_book("The Hobbit")
    updated = service.update_status(book.id, "reading")
    assert updated.status == "reading"
    assert [item.id for item in service.repository.list_books("reading")] == [book.id]
    assert service.repository.list_books("finished") == []
    assert set(READING_STATUSES) >= {updated.status}


def test_search_title_author_and_description(service):
    service.add_book("Dune", "Frank Herbert", description="Desert planet")
    assert len(service.repository.search_books("frank")) == 1
    assert len(service.repository.search_books("desert")) == 1
    assert service.repository.search_books("nonexistent") == []


def test_notes_are_attached_to_existing_book(service):
    book = service.add_book("Atomic Habits")
    note = service.add_note(book.id, "Make it obvious", "Chapter 1")
    assert note.book_id == book.id
    assert note.page_reference == "Chapter 1"
    assert service.repository.list_notes(book.id)[0].note == "Make it obvious"


def test_rejects_empty_note_and_unknown_book(service):
    with pytest.raises(ReadingValidationError, match="cannot be empty"):
        service.add_note(1, "  ")
    with pytest.raises(ReadingValidationError, match="does not exist"):
        service.add_note(999, "Note")


def test_progress_validation_and_latest_record(service):
    book = service.add_book("Project Hail Mary", book_format="audiobook")
    first = service.record_progress(book.id, 15, "percent")
    second = service.record_progress(book.id, 42, "percent")
    assert first.progress_value == 15
    assert service.repository.latest_progress(book.id).id == second.id
    with pytest.raises(ReadingValidationError, match="cannot exceed"):
        service.record_progress(book.id, 101, "percent")
    with pytest.raises(ReadingValidationError, match="cannot be negative"):
        service.record_progress(book.id, -1, "page")


def test_reading_lists_are_deduplicated(service):
    book = service.add_book("The Martian")
    list_id = service.repository.create_list("Sci-fi", "Science fiction books")
    service.repository.add_to_list(list_id, book.id)
    service.repository.add_to_list(list_id, book.id)
    assert [item.id for item in service.repository.list_contents(list_id)] == [book.id]


def test_book_deletion_cascade_is_enforced_by_database(service):
    book = service.add_book("Test")
    service.add_note(book.id, "Note")
    service.record_progress(book.id, 1, "page")
    with service.repository._connection() as conn:
        conn.execute("DELETE FROM reading_books WHERE id = ?", (book.id,))
        assert conn.execute("SELECT COUNT(*) FROM reading_notes").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM reading_progress").fetchone()[0] == 0
