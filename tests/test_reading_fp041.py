"""Regression tests for the current FP041 Reading Foundation API.

This file replaces an obsolete test module that targeted a superseded API.
"""
import pytest

from reading import ReadingRepository, ReadingService
from reading.providers import BorrowBoxProvider


@pytest.fixture
def service(tmp_path):
    repository = ReadingRepository(tmp_path / "reading-legacy-compat.db")
    return ReadingService(repository=repository)


def test_add_book_and_defaults(service):
    book = service.add_book("Dune", "Frank Herbert", book_format="ebook")
    assert book.id > 0
    assert book.status == "want_to_read"
    assert service.repository.summary()["total"] == 1


def test_status_and_progress(service):
    book = service.add_book("The Hobbit")
    service.update_status(book.id, "reading")
    progress = service.record_progress(book.id, 35, "percent")
    assert progress.progress_value == 35
    assert service.repository.latest_progress(book.id).id == progress.id
    assert service.update_status(book.id, "finished").status == "finished"


def test_progress_validation(service):
    book = service.add_book("Test")
    with pytest.raises(ValueError):
        service.record_progress(book.id, -1)
    with pytest.raises(ValueError):
        service.record_progress(book.id, 101)


def test_notes_and_lists(service):
    book = service.add_book("Atomic Habits")
    note = service.add_note(book.id, "A useful idea", "Chapter 2")
    assert note.book_id == book.id
    list_id = service.repository.create_list("Non-fiction")
    service.repository.add_to_list(list_id, book.id)
    service.repository.add_to_list(list_id, book.id)
    assert [item.id for item in service.repository.list_contents(list_id)] == [book.id]


def test_borrowbox_sync_remains_disabled():
    provider = BorrowBoxProvider()
    assert provider.get_launch_url() == "https://www.borrowbox.com/"
    with pytest.raises(NotImplementedError):
        provider.sync()
