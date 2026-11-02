"""SQLite persistence for reading data, isolated from Kaivor's other stores."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from reading.models import Book, ReadingNote, ReadingProgress

DEFAULT_DB_PATH = Path("data/reading.db")


class ReadingRepository:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialise(self) -> None:
        with self._connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS reading_books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT,
                    book_format TEXT NOT NULL DEFAULT 'other',
                    status TEXT NOT NULL DEFAULT 'want_to_read',
                    provider TEXT,
                    provider_item_id TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(provider, provider_item_id)
                );
                CREATE INDEX IF NOT EXISTS idx_reading_books_status
                    ON reading_books(status);
                CREATE INDEX IF NOT EXISTS idx_reading_books_title
                    ON reading_books(title COLLATE NOCASE);
                CREATE TABLE IF NOT EXISTS reading_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL REFERENCES reading_books(id) ON DELETE CASCADE,
                    note TEXT NOT NULL,
                    page_reference TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_reading_notes_book
                    ON reading_notes(book_id, created_at);
                CREATE TABLE IF NOT EXISTS reading_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL REFERENCES reading_books(id) ON DELETE CASCADE,
                    progress_value REAL NOT NULL CHECK(progress_value >= 0),
                    progress_unit TEXT NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_reading_progress_book
                    ON reading_progress(book_id, recorded_at);
                CREATE TABLE IF NOT EXISTS reading_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS reading_list_items (
                    list_id INTEGER NOT NULL REFERENCES reading_lists(id) ON DELETE CASCADE,
                    book_id INTEGER NOT NULL REFERENCES reading_books(id) ON DELETE CASCADE,
                    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(list_id, book_id)
                );
            """)

    @staticmethod
    def _book(row: sqlite3.Row | None) -> Book | None:
        return Book(**dict(row)) if row else None

    def add_book(self, title: str, author: str | None = None, book_format: str = "other",
                 status: str = "want_to_read", provider: str | None = None,
                 provider_item_id: str | None = None, description: str | None = None) -> Book:
        with self._connection() as conn:
            cur = conn.execute("""INSERT INTO reading_books
                (title, author, book_format, status, provider, provider_item_id, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (title, author, book_format, status, provider, provider_item_id, description))
            row = conn.execute("SELECT * FROM reading_books WHERE id = ?", (cur.lastrowid,)).fetchone()
            return self._book(row)  # type: ignore[return-value]

    def get_book(self, book_id: int) -> Book | None:
        with self._connection() as conn:
            return self._book(conn.execute("SELECT * FROM reading_books WHERE id = ?", (book_id,)).fetchone())

    def list_books(self, status: str | None = None) -> list[Book]:
        sql, params = "SELECT * FROM reading_books", ()
        if status:
            sql, params = sql + " WHERE status = ?", (status,)
        sql += " ORDER BY updated_at DESC, id DESC"
        with self._connection() as conn:
            return [self._book(row) for row in conn.execute(sql, params).fetchall()]  # type: ignore[misc]

    def search_books(self, query: str) -> list[Book]:
        term = f"%{query}%"
        with self._connection() as conn:
            rows = conn.execute("""SELECT * FROM reading_books
                WHERE title LIKE ? COLLATE NOCASE OR author LIKE ? COLLATE NOCASE
                OR description LIKE ? COLLATE NOCASE ORDER BY title COLLATE NOCASE""",
                (term, term, term)).fetchall()
            return [self._book(row) for row in rows]  # type: ignore[misc]

    def update_book(self, book_id: int, **fields: str | None) -> Book | None:
        allowed = {"title", "author", "book_format", "status", "description"}
        updates = {key: value for key, value in fields.items() if key in allowed and value is not None}
        if not updates:
            return self.get_book(book_id)
        assignments = ", ".join(f"{key} = ?" for key in updates)
        with self._connection() as conn:
            conn.execute(f"UPDATE reading_books SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                         (*updates.values(), book_id))
            row = conn.execute("SELECT * FROM reading_books WHERE id = ?", (book_id,)).fetchone()
            return self._book(row)

    def add_note(self, book_id: int, note: str, page_reference: str | None = None) -> ReadingNote:
        with self._connection() as conn:
            cur = conn.execute("INSERT INTO reading_notes (book_id, note, page_reference) VALUES (?, ?, ?)",
                               (book_id, note, page_reference))
            row = conn.execute("SELECT * FROM reading_notes WHERE id = ?", (cur.lastrowid,)).fetchone()
            return ReadingNote(**dict(row))

    def list_notes(self, book_id: int) -> list[ReadingNote]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM reading_notes WHERE book_id = ? ORDER BY created_at, id",
                                (book_id,)).fetchall()
            return [ReadingNote(**dict(row)) for row in rows]

    def record_progress(self, book_id: int, value: float, unit: str) -> ReadingProgress:
        with self._connection() as conn:
            cur = conn.execute("INSERT INTO reading_progress (book_id, progress_value, progress_unit) VALUES (?, ?, ?)",
                               (book_id, value, unit))
            row = conn.execute("SELECT * FROM reading_progress WHERE id = ?", (cur.lastrowid,)).fetchone()
            return ReadingProgress(**dict(row))

    def list_progress(self, book_id: int) -> list[ReadingProgress]:
        """Return progress records newest first for a book."""
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM reading_progress WHERE book_id = ? ORDER BY recorded_at DESC, id DESC", (book_id,)).fetchall()
            return [ReadingProgress(**dict(row)) for row in rows]

    def latest_progress(self, book_id: int) -> ReadingProgress | None:
        with self._connection() as conn:
            row = conn.execute("""SELECT * FROM reading_progress WHERE book_id = ?
                ORDER BY recorded_at DESC, id DESC LIMIT 1""", (book_id,)).fetchone()
            return ReadingProgress(**dict(row)) if row else None

    def create_list(self, name: str, description: str | None = None) -> int:
        with self._connection() as conn:
            cur = conn.execute("INSERT INTO reading_lists (name, description) VALUES (?, ?)", (name, description))
            return int(cur.lastrowid)

    def add_to_list(self, list_id: int, book_id: int) -> None:
        with self._connection() as conn:
            conn.execute("INSERT OR IGNORE INTO reading_list_items (list_id, book_id) VALUES (?, ?)",
                         (list_id, book_id))

    def list_contents(self, list_id: int) -> list[Book]:
        with self._connection() as conn:
            rows = conn.execute("""SELECT b.* FROM reading_books b
                JOIN reading_list_items i ON i.book_id = b.id
                WHERE i.list_id = ? ORDER BY i.added_at, b.title COLLATE NOCASE""", (list_id,)).fetchall()
            return [self._book(row) for row in rows]  # type: ignore[misc]


    def list_lists(self) -> list[dict]:
        """Return reading lists with their current book counts."""
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT l.id, l.name, l.description, l.created_at,
                       COUNT(i.book_id) AS book_count
                FROM reading_lists AS l
                LEFT JOIN reading_list_items AS i ON i.list_id = l.id
                GROUP BY l.id
                ORDER BY l.name COLLATE NOCASE
            """).fetchall()
            return [dict(row) for row in rows]

    def delete_book(self, book_id: int) -> bool:
        """Delete a book and rely on foreign-key cascades for related records."""
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM reading_books WHERE id = ?", (int(book_id),))
            return cursor.rowcount > 0

    def dashboard_snapshot(self) -> dict:
        """Load the complete Reading dashboard using one database connection.

        The latest progress and note counts are joined in SQL to avoid the
        per-book query/connection pattern used by the original dashboard.
        """
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT b.*,
                       p.id AS progress_id,
                       p.book_id AS progress_book_id,
                       p.progress_value AS progress_value,
                       p.progress_unit AS progress_unit,
                       p.recorded_at AS progress_recorded_at,
                       COALESCE(n.notes_count, 0) AS notes_count
                FROM reading_books AS b
                LEFT JOIN reading_progress AS p
                  ON p.id = (
                    SELECT p2.id FROM reading_progress AS p2
                    WHERE p2.book_id = b.id
                    ORDER BY p2.recorded_at DESC, p2.id DESC
                    LIMIT 1
                  )
                LEFT JOIN (
                    SELECT book_id, COUNT(*) AS notes_count
                    FROM reading_notes GROUP BY book_id
                ) AS n ON n.book_id = b.id
                ORDER BY b.updated_at DESC, b.id DESC
            """).fetchall()

            books = []
            for row in rows:
                data = dict(row)
                progress = None
                if data["progress_id"] is not None:
                    progress = ReadingProgress(
                        id=data["progress_id"],
                        book_id=data["progress_book_id"],
                        progress_value=data["progress_value"],
                        progress_unit=data["progress_unit"],
                        recorded_at=data["progress_recorded_at"],
                    )
                book_data = {key: data[key] for key in (
                    "id", "title", "author", "book_format", "status", "provider",
                    "provider_item_id", "description", "created_at", "updated_at"
                )}
                books.append({
                    "book": Book(**book_data),
                    "progress": progress,
                    "notes_count": int(data["notes_count"] or 0),
                })

            counts = {
                row["status"]: int(row["count"])
                for row in conn.execute(
                    "SELECT status, COUNT(*) AS count FROM reading_books GROUP BY status"
                ).fetchall()
            }
            total = sum(counts.values())
            notes = int(conn.execute("SELECT COUNT(*) FROM reading_notes").fetchone()[0])
            lists = int(conn.execute("SELECT COUNT(*) FROM reading_lists").fetchone()[0])
            list_rows = conn.execute("""
                SELECT l.id, l.name, l.description, l.created_at,
                       COUNT(i.book_id) AS book_count
                FROM reading_lists AS l
                LEFT JOIN reading_list_items AS i ON i.list_id = l.id
                GROUP BY l.id
                ORDER BY l.name COLLATE NOCASE
            """).fetchall()

        return {
            "summary": {
                "total": total,
                "by_status": counts,
                "notes": notes,
                "lists": lists,
            },
            "books": books,
            "lists": [dict(row) for row in list_rows],
        }

    def summary(self) -> dict:
        """Return aggregate counts without exposing note contents."""
        with self._connection() as conn:
            counts = {
                row["status"]: row["count"]
                for row in conn.execute(
                    "SELECT status, COUNT(*) AS count FROM reading_books GROUP BY status"
                ).fetchall()
            }
            total = sum(counts.values())
            notes = conn.execute("SELECT COUNT(*) FROM reading_notes").fetchone()[0]
            lists = conn.execute("SELECT COUNT(*) FROM reading_lists").fetchone()[0]
            return {
                "total": total,
                "by_status": counts,
                "notes": int(notes),
                "lists": int(lists),
            }
