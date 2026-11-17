"""
Kaivor Tasks — PostgreSQL store (FP114, FP118).

Backed by the public.tasks table in the Supabase database Reading
already uses (KAIVOR_READING_DATABASE_URL). The schema comes from
the versioned migrations
migrations/reading/002_memories_tasks_fp113_fp114.sql (the table)
and migrations/reading/003_task_due_time_alerts_fp118.sql (the
due_time and alerted_at columns) — never created by the app.

Postgres-only: unlike memories, tasks have no SQLite/JSON fallback.
When no database URL is configured, task_store_or_none() returns None
and the routes report not configured (503) instead of inventing a
store. psycopg is imported lazily — it has no Termux wheel.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from typing import Iterator
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")

_COLUMNS = "id, title, notes, due_date, due_time, done, created_at, updated_at, alerted_at"


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
        # date, due_time is a time, and the timestamps are datetimes
        # from Postgres; turn them into plain strings so the row is
        # JSON-safe. alerted_at is None until the task has alerted.
        values = list(row)
        if isinstance(values[3], date):
            values[3] = values[3].isoformat()
        if isinstance(values[4], time):
            values[4] = values[4].strftime("%H:%M")
        for index in (6, 7, 8):
            if isinstance(values[index], datetime):
                values[index] = values[index].strftime("%Y-%m-%d %H:%M:%S")
        keys = ("id", "title", "notes", "due_date", "due_time", "done", "created_at", "updated_at", "alerted_at")
        return dict(zip(keys, values))

    def list_tasks(self):
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT {_COLUMNS}
                FROM public.tasks
                ORDER BY done ASC, due_date ASC NULLS LAST, due_time ASC NULLS LAST, created_at DESC, id DESC
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

    def add_task(self, title, notes="", due_date=None, due_time=None):
        with self._connection() as conn:
            row = conn.execute(
                """
                INSERT INTO public.tasks (title, notes, due_date, due_time)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (title, notes, due_date, due_time),
            ).fetchone()
            return row[0]

    def update_task(self, task_id, **fields):
        allowed = {"title", "notes", "due_date", "due_time", "done", "alerted_at"}
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

    def due_tasks(self, now=None, window_minutes=15, grace_minutes=60, limit=20):
        """Tasks due soon that have not alerted yet (FP118).

        Only tasks with BOTH a due date and a due time can alert —
        a date-only task has no moment to fire at. A task counts as
        due when its due moment falls between (now - grace) and
        (now + window): the grace catches tasks that went due while
        the checker was briefly down, and alerted_at (set by
        mark_alerted) makes sure each task fires once. Due moments
        are Europe/London wall-clock, like the rest of Kaivor.
        """
        if now is None:
            now = datetime.now(LONDON)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=LONDON)
        earliest = now - timedelta(minutes=grace_minutes)
        latest = now + timedelta(minutes=window_minutes)
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT {_COLUMNS}
                FROM public.tasks
                WHERE done = FALSE AND due_date IS NOT NULL
                  AND due_time IS NOT NULL AND alerted_at IS NULL
                ORDER BY due_date ASC, due_time ASC
                """
            ).fetchall()
        due = []
        for row in rows:
            due_moment = datetime.combine(row[3], row[4], tzinfo=LONDON)
            if earliest <= due_moment <= latest:
                due.append(self._task(row))
                if len(due) >= limit:
                    break
        return due

    def mark_alerted(self, task_id):
        """Record that a task's alert has fired, so it fires once."""
        with self._connection() as conn:
            row = conn.execute(
                "UPDATE public.tasks SET alerted_at = now() WHERE id = %s RETURNING id",
                (task_id,),
            ).fetchone()
            return row is not None


def task_store_or_none():
    """The task store, or None when no database URL is configured."""
    database_url = os.environ.get("KAIVOR_READING_DATABASE_URL", "").strip()
    if not database_url:
        return None
    return PostgresTaskStore(database_url)
