import tempfile
import unittest
from pathlib import Path
from core.reading import ReadingRepository, ReadingService


class ReadingFoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = ReadingRepository(Path(self.temp.name) / "reading.sqlite3")
        self.service = ReadingService(self.repo)

    def tearDown(self):
        self.temp.cleanup()

    def test_add_and_search_book(self):
        book = self.service.add_book(title="Atomic Habits", authors="James Clear")
        self.assertGreater(book.id, 0)
        self.assertEqual(self.service.search("atomic")[0].title, "Atomic Habits")

    def test_progress_updates_status(self):
        book = self.service.add_book(title="Book")
        updated = self.service.record_progress(book.id, 35)
        self.assertEqual(updated.status, "reading")
        self.assertEqual(updated.progress, 35)
        self.assertEqual(self.service.record_progress(book.id, 100).status, "completed")

    def test_invalid_progress_rejected(self):
        book = self.service.add_book(title="Book")
        with self.assertRaises(ValueError):
            self.service.record_progress(book.id, 101)

    def test_notes_are_book_linked(self):
        book = self.service.add_book(title="Book")
        note = self.service.add_note(book.id, "Remember this idea", "idea")
        self.assertEqual(self.repo.list_notes(book.id)[0].id, note.id)

    def test_empty_note_rejected(self):
        book = self.service.add_book(title="Book")
        with self.assertRaises(ValueError):
            self.service.add_note(book.id, " ")

    def test_lists_are_ordered_and_idempotent(self):
        first = self.service.add_book(title="First")
        second = self.service.add_book(title="Second")
        reading_list = self.repo.create_list("Weekend")
        self.repo.add_to_list(reading_list.id, first.id)
        self.repo.add_to_list(reading_list.id, second.id)
        self.repo.add_to_list(reading_list.id, first.id)
        self.assertEqual([b.id for b in self.repo.list_items(reading_list.id)],
                         [first.id, second.id])

    def test_provider_id_is_idempotent(self):
        a = self.repo.add_book("Original", provider="borrowbox", provider_id="abc")
        b = self.repo.add_book("Updated title", provider="borrowbox", provider_id="abc")
        self.assertEqual(a.id, b.id)
        self.assertEqual(self.repo.summary()["books"], 1)

    def test_bad_status_and_format_rejected(self):
        with self.assertRaises(ValueError):
            self.repo.list_books(status="unknown")
        with self.assertRaises(ValueError):
            self.repo.add_book("Book", format="unknown")

    def test_dashboard_counts(self):
        book = self.service.add_book(title="Book")
        self.service.add_note(book.id, "Note")
        self.repo.create_list("To explore")
        summary = self.service.reading_dashboard()
        self.assertEqual(summary["books"], 1)
        self.assertEqual(summary["notes"], 1)
        self.assertEqual(summary["lists"], 1)


if __name__ == "__main__":
    unittest.main()
