"""
Kaivor Tasks — PostgreSQL store (FP114).

Backed by the public.tasks table in the Supabase database Reading
already uses (KAIVOR_READING_DATABASE_URL). The schema comes from
the versioned migration
migrations/reading/002_memories_tasks_fp113_fp114.sql — never
created by the app.

Postgres-only: unlike memories, tasks have no SQLite/JSON fallback.
When no database URL is configured, task_store_or_none() returns None
and the routes report not configured (503) instead of inventing a
store. psycopg is imported lazily — it has no Termux wheel.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator

_COLUMNS = "id, title, notes, due_date, done, created_at, updated_at"


class PostgresTaskStore:
    """PostgreSQL task storage."""

    def __init__(self, database_url: str):
        self.database_url = str(database_url or "").strip()
        if not self.database_url:
            raise ValueError("KAIVOR_READING_DATABASE_URL is required.")
        if not self.database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("Tasks database URL must use postgresql://.")
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
                "PostgreSQL task storage requires psycopg. "
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
    def _task(row):
        # Rows come back as tuples in _COLUMNS order. due_date is a
        # date and the timestamps are datetimes from Postgres; turn
        # them into plain strings so the row is JSON-safe.
        values = list(row)
        if isinstance(values[3], date):
            values[3] = values[3].isoformat()
        for index in (5, 6):
            if isinstance(values[index], datetime):
                values[index] = values[index].strftime("%Y-%m-%d %H:%M:%S")
        keys = ("id", "title", "notes", "due_date", "done", "created_at", "updated_at")
        return dict(zip(keys, values))

    def list_tasks(self):
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT {_COLUMNS}
                FROM public.tasks
                ORDER BY done ASC, due_date ASC NULLS LAST, created_at DESC, id DESC
                """
            ).fetchall()
            return [self._task(row) for row in rows]

    def get_task(self, task_id):
        with self._connection() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM public.tasks WHERE id = %s",
                (task_id,),
            ).fetchone()
            return self._task(row) if row else None

    def add_task(self, title, notes="", due_date=None):
        with self._connection() as conn:
            row = conn.execute(
                """
                INSERT INTO public.tasks (title, notes, due_date)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (title, notes, due_date),
            ).fetchone()
            return row[0]

    def update_task(self, task_id, **fields):
        allowed = {"title", "notes", "due_date", "done"}
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return self.get_task(task_id)
        assignments = ", ".join(f"{key} = %s" for key in updates)
        with self._connection() as conn:
            row = conn.execute(
                f"""
                UPDATE public.tasks
                SET {assignments}, updated_at = now()
                WHERE id = %s
                RETURNING {_COLUMNS}
                """,
                (*updates.values(), task_id),
            ).fetchone()
            return self._task(row) if row else None

    def delete_task(self, task_id):
        with self._connection() as conn:
            row = conn.execute(
                "DELETE FROM public.tasks WHERE id = %s RETURNING id",
                (task_id,),
            ).fetchone()
            return row is not None


def task_store_or_none():
    """The task store, or None when no database URL is configured."""
    database_url = os.environ.get("KAIVOR_READING_DATABASE_URL", "").strip()
    if not database_url:
        return None
    return PostgresTaskStore(database_url)
