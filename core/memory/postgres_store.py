"""
Kaivor Memory — PostgreSQL store (FP113).

Same interface as core.memory.manager.MemoryManager, backed by the
public.memories table in the Supabase database Reading already uses
(KAIVOR_READING_DATABASE_URL). The schema comes from the versioned
migration migrations/reading/002_memories_tasks_fp113_fp114.sql —
never created by the app.

psycopg is imported lazily inside _connection(): it has no Termux
wheel, so importing this module on the phone must stay safe. The
store is only constructed when a database URL is configured (see
core.memory.api._get_manager).
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from core.memory.models import Memory

_COLUMNS = "id, category, title, content, created_at, importance, source, tags"


class PostgresMemoryStore:
    """PostgreSQL implementation matching the MemoryManager API."""

    def __init__(self, database_url: str):
        self.database_url = str(database_url or "").strip()
        if not self.database_url:
            raise ValueError("KAIVOR_READING_DATABASE_URL is required.")
        if not self.database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("Memory database URL must use postgresql://.")
        # Require TLS even if a manually copied URI omitted the query option.
        if "sslmode=" not in self.database_url.lower():
            separator = "&" if "?" in self.database_url else "?"
            self.database_url += f"{separator}sslmode=require"

    @contextmanager
    def _connection(self) -> Iterator[object]:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL memory storage requires psycopg. "
                "Install requirements-postgres.txt."
            ) from exc

        conn = psycopg.connect(
            self.database_url,
            connect_timeout=10,
            prepare_threshold=None,  # Required for PgBouncer transaction pooling.
        )
        try:
            with conn.transaction():
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _memory(row):
        # Rows come back as tuples in _COLUMNS order. created_at is a
        # datetime from Postgres; format it exactly like the SQLite
        # store's CURRENT_TIMESTAMP string so both backends produce
        # identical Memory objects.
        values = list(row)
        created = values[4]
        if isinstance(created, datetime):
            values[4] = created.strftime("%Y-%m-%d %H:%M:%S")
        return Memory.from_row(values)

    def add_memory(self, category, title, content, importance=3, source="manual", tags=""):
        with self._connection() as conn:
            row = conn.execute(
                """
                INSERT INTO public.memories
                (category, title, content, importance, source, tags)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (category, title, content, importance, source, tags),
            ).fetchone()
            return row[0]

    def delete_memory(self, memory_id):
        """Delete one memory. Returns True when a row was removed."""
        with self._connection() as conn:
            row = conn.execute(
                "DELETE FROM public.memories WHERE id = %s RETURNING id",
                (memory_id,),
            ).fetchone()
            return row is not None

    def get_memories(self):
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT {_COLUMNS}
                FROM public.memories
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
            return [self._memory(row) for row in rows]

    def get_memories_by_category(self, category):
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT {_COLUMNS}
                FROM public.memories
                WHERE category = %s
                ORDER BY created_at DESC, id DESC
                """,
                (category,),
            ).fetchall()
            return [self._memory(row) for row in rows]

    def search_memories(self, keyword):
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT {_COLUMNS}
                FROM public.memories
                WHERE title ILIKE %s
                   OR content ILIKE %s
                ORDER BY created_at DESC, id DESC
                """,
                (f"%{keyword}%", f"%{keyword}%"),
            ).fetchall()
            return [self._memory(row) for row in rows]
