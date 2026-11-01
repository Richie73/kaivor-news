import tempfile
import unittest
from pathlib import Path
from modules.reading import ReadingService

class ReadingServiceTests(unittest.TestCase):
    def setUp(self): self.svc=ReadingService(":memory:")
    def tearDown(self): self.svc.close()
    def test_add_search_and_update_book(self):
        b=self.svc.add_book("Atomic Habits", "James Clear", format="ebook")
        self.assertEqual(self.svc.get_book(b.id).title,"Atomic Habits")
        self.assertEqual(len(self.svc.list_books(query="clear")),1)
        self.assertEqual(self.svc.update_book(b.id,status="reading").status,"reading")
    def test_validation(self):
        with self.assertRaises(ValueError): self.svc.add_book(" ")
        with self.assertRaises(ValueError): self.svc.add_book("X",status="magic")
    def test_progress(self):
        b=self.svc.add_book("Book")
        self.assertEqual(self.svc.set_progress(b.id,42,unit="percent")["value"],42)
        with self.assertRaises(ValueError): self.svc.set_progress(b.id,101)
    def test_notes_require_existing_book(self):
        b=self.svc.add_book("Book")
        self.svc.add_note(b.id,"A useful idea",kind="idea",locator="Chapter 2")
        self.assertEqual(self.svc.list_notes(b.id)[0].body,"A useful idea")
        with self.assertRaises(KeyError): self.svc.add_note("missing","note")
    def test_reading_lists_and_summary(self):
        b=self.svc.add_book("Book")
        reading_list=self.svc.create_list("AI fundamentals")
        self.svc.add_to_list(reading_list.id,b.id)
        self.assertEqual(self.svc.get_list_books(reading_list.id)[0].id,b.id)
        self.assertEqual(self.svc.summary()["total_books"],1)
    def test_delete_book_cascades_notes(self):
        b=self.svc.add_book("Book")
        self.svc.add_note(b.id,"Note")
        with self.svc._conn: self.svc._conn.execute("DELETE FROM reading_books WHERE id=?",(b.id,))
        self.assertEqual(self.svc._conn.execute("SELECT COUNT(*) FROM reading_notes").fetchone()[0],0)

if __name__ == "__main__": unittest.main()
