"""PostgreSQL persistence adapter for Kaivor Reading (Supabase).

Uses the Supabase transaction-pooler connection string supplied only through
KAIVOR_READING_DATABASE_URL. Schema creation is deliberately handled by the
versioned SQL migration, never automatically by the web application.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator


class PostgresReadingRepository:
    """PostgreSQL implementation matching the SQLite ReadingRepository API."""

    def __init__(self, database_url: str):
        self.database_url = str(database_url or "").strip()
        if not self.database_url:
            raise ValueError("KAIVOR_READING_DATABASE_URL is required.")
        if not self.database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("Reading database URL must use postgresql://.")
        # Require TLS even if a manually copied URI omitted the query option.
        if "sslmode=" not in self.database_url.lower():
            separator = "&" if "?" in self.database_url else "?"
            self.database_url += f"{separator}sslmode=require"

    @contextmanager
    def _connection(self) -> Iterator[object]:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL Reading storage requires psycopg. Install requirements.txt."
            ) from exc

        conn = psycopg.connect(
            self.database_url,
            row_factory=dict_row,
            connect_timeout=10,
            prepare_threshold=None,  # Required for PgBouncer transaction pooling.
        )
        try:
            with conn.transaction():
                yield conn
        except Exception as exc:
            # Keep the existing Flask API's duplicate/constraint handling
            # consistent between SQLite and PostgreSQL.
            if isinstance(exc, psycopg.IntegrityError):
                raise sqlite3.IntegrityError(str(exc)) from exc
            raise
        finally:
            conn.close()

    @staticmethod
    def _normalise(row):
        if row is None:
            return None
        result = dict(row)
        for key, value in result.items():
            if isinstance(value, (datetime, date)):
                result[key] = value.isoformat()
        return result

    @classmethod
    def _book(cls, row):
        from reading.models import Book
        data = cls._normalise(row)
        return Book(**data) if data else None

    @classmethod
    def _note(cls, row):
        from reading.models import ReadingNote
        data = cls._normalise(row)
        return ReadingNote(**data) if data else None

    @classmethod
    def _progress(cls, row):
        from reading.models import ReadingProgress
        data = cls._normalise(row)
        return ReadingProgress(**data) if data else None

    def add_book(self, title, author=None, book_format="other",
                 status="want_to_read", provider=None,
                 provider_item_id=None, description=None):
        with self._connection() as conn:
            row = conn.execute(
                """INSERT INTO public.reading_books
                   (title, author, book_format, status, provider, provider_item_id, description)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (title, author, book_format, status, provider, provider_item_id, description),
            ).fetchone()
            return self._book(row)

    def get_book(self, book_id):
        with self._connection() as conn:
            return self._book(conn.execute(
                "SELECT * FROM public.reading_books WHERE id = %s", (book_id,)
            ).fetchone())

    def list_books(self, status=None):
        sql = "SELECT * FROM public.reading_books"
        params = ()
        if status:
            sql += " WHERE status = %s"
            params = (status,)
        sql += " ORDER BY updated_at DESC, id DESC"
        with self._connection() as conn:
            return [self._book(row) for row in conn.execute(sql, params).fetchall()]

    def search_books(self, query):
        term = f"%{query}%"
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT * FROM public.reading_books
                   WHERE title ILIKE %s OR author ILIKE %s OR description ILIKE %s
                   ORDER BY title""",
                (term, term, term),
            ).fetchall()
            return [self._book(row) for row in rows]

    def update_book(self, book_id, **fields):
        allowed = {"title", "author", "book_format", "status", "description"}
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return self.get_book(book_id)
        assignments = ", ".join(f"{key} = %s" for key in updates)
        with self._connection() as conn:
            row = conn.execute(
                f"""UPDATE public.reading_books
                    SET {assignments}, updated_at = now()
                    WHERE id = %s RETURNING *""",
                (*updates.values(), book_id),
            ).fetchone()
            return self._book(row)

    def add_note(self, book_id, note, page_reference=None):
        with self._connection() as conn:
            row = conn.execute(
                """INSERT INTO public.reading_notes (book_id, note, page_reference)
                   VALUES (%s, %s, %s) RETURNING *""",
                (book_id, note, page_reference),
            ).fetchone()
            return self._note(row)

    def list_notes(self, book_id):
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT * FROM public.reading_notes
                   WHERE book_id = %s ORDER BY created_at, id""",
                (book_id,),
            ).fetchall()
            return [self._note(row) for row in rows]

    def record_progress(self, book_id, value, unit):
        with self._connection() as conn:
            row = conn.execute(
                """INSERT INTO public.reading_progress (book_id, progress_value, progress_unit)
                   VALUES (%s, %s, %s) RETURNING *""",
                (book_id, value, unit),
            ).fetchone()
            return self._progress(row)

    def list_progress(self, book_id):
        """Return progress records newest first for a book."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM public.reading_progress WHERE book_id = %s ORDER BY recorded_at DESC, id DESC",
                (book_id,),
            ).fetchall()
            return [self._progress(row) for row in rows]

    def latest_progress(self, book_id):
        with self._connection() as conn:
            row = conn.execute(
                """SELECT * FROM public.reading_progress
                   WHERE book_id = %s ORDER BY recorded_at DESC, id DESC LIMIT 1""",
                (book_id,),
            ).fetchone()
            return self._progress(row)

    def create_list(self, name, description=None):
        with self._connection() as conn:
            row = conn.execute(
                """INSERT INTO public.reading_lists (name, description)
                   VALUES (%s, %s) RETURNING id""",
                (name, description),
            ).fetchone()
            return int(row["id"])

    def add_to_list(self, list_id, book_id):
        with self._connection() as conn:
            conn.execute(
                """INSERT INTO public.reading_list_items (list_id, book_id)
                   VALUES (%s, %s) ON CONFLICT (list_id, book_id) DO NOTHING""",
                (list_id, book_id),
            )

    def list_contents(self, list_id):
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT b.* FROM public.reading_books AS b
                   JOIN public.reading_list_items AS i ON i.book_id = b.id
                   WHERE i.list_id = %s
                   ORDER BY i.added_at, b.title""",
                (list_id,),
            ).fetchall()
            return [self._book(row) for row in rows]

    def list_lists(self):
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT l.id, l.name, l.description, l.created_at,
                          COUNT(i.book_id) AS book_count
                   FROM public.reading_lists AS l
                   LEFT JOIN public.reading_list_items AS i ON i.list_id = l.id
                   GROUP BY l.id
                   ORDER BY l.name"""
            ).fetchall()
            return [self._normalise(row) for row in rows]

    def delete_book(self, book_id):
        with self._connection() as conn:
            row = conn.execute(
                "DELETE FROM public.reading_books WHERE id = %s RETURNING id",
                (int(book_id),),
            ).fetchone()
            return row is not None

    def summary(self):
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT status, COUNT(*) AS count
                   FROM public.reading_books GROUP BY status"""
            ).fetchall()
            counts = {row["status"]: row["count"] for row in rows}
            total = sum(counts.values())
            notes = conn.execute("SELECT COUNT(*) AS count FROM public.reading_notes").fetchone()["count"]
            lists = conn.execute("SELECT COUNT(*) AS count FROM public.reading_lists").fetchone()["count"]
            return {
                "total": int(total),
                "by_status": {key: int(value) for key, value in counts.items()},
                "notes": int(notes),
                "lists": int(lists),
            }
