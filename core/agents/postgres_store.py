"""PostgreSQL task-store adapter for hosted Kaivor MCP deployments."""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_SECURE_SSL_MODES = {"require", "verify-ca", "verify-full"}


def _secure_database_uri(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not parsed.path.strip("/"):
        raise ValueError("KAIVOR_AGENT_DATABASE_URL must be a valid PostgreSQL connection URI.")
    query = parse_qsl(parsed.query, keep_blank_values=True)
    ssl_values = [item for key, item in query if key.casefold() == "sslmode"]
    if len(ssl_values) > 1:
        raise ValueError("PostgreSQL URI may contain at most one sslmode parameter.")
    if ssl_values and ssl_values[0].casefold() not in _SECURE_SSL_MODES:
        raise ValueError("PostgreSQL connection requires TLS; sslmode must be require, verify-ca, or verify-full.")
    if not ssl_values:
        query.append(("sslmode", "require"))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


class PostgresAgentTaskStore:
    """AgentTaskStore-compatible adapter using psycopg 3 and PostgreSQL."""

    def __init__(self, database_url: str | None = None) -> None:
        raw_url = (database_url or os.environ.get("KAIVOR_AGENT_DATABASE_URL", "")).strip()
        if not raw_url:
            raise ValueError("KAIVOR_AGENT_DATABASE_URL must be a PostgreSQL connection URI.")
        self.database_url = _secure_database_uri(raw_url)

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("PostgreSQL task storage requires psycopg; install requirements-postgres.txt.") from exc
        conn = psycopg.connect(self.database_url, row_factory=dict_row, connect_timeout=10, prepare_threshold=None)
        try:
            with conn.transaction():
                yield conn
        finally:
            conn.close()

    def health_check(self) -> bool:
        with self._connection() as conn:
            return conn.execute("SELECT 1 AS healthy").fetchone()["healthy"] == 1

    @staticmethod
    def _record(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "task_id": row["task_id"], "assigned_to": row["assigned_to"],
            "task_type": row["task_type"], "status": row["status"],
            "task": row["task_json"] if isinstance(row["task_json"], dict) else json.loads(row["task_json"]),
            "result": row["result_json"] if isinstance(row["result_json"], dict) else (json.loads(row["result_json"]) if row["result_json"] else None),
            "error_code": row["error_code"],
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else row["created_at"],
            "updated_at": row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else row["updated_at"],
        }

    def create(self, task: dict[str, Any], status: str) -> None:
        with self._connection() as conn:
            conn.execute("""INSERT INTO public.agent_tasks
                (task_id, assigned_to, task_type, status, task_json, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::timestamptz, %s::timestamptz)""",
                (task["task_id"], task["assigned_to"], task["task_type"], status,
                 json.dumps(task, ensure_ascii=False), task["created_at"], task["created_at"]))

    def update(self, task_id: str, status: str, *, result: dict[str, Any] | None = None,
               error_code: str | None = None, task: dict[str, Any] | None = None,
               updated_at: str, expected_status: str | None = None) -> None:
        query = "UPDATE public.agent_tasks SET status=%s, result_json=%s::jsonb, error_code=%s, task_json=COALESCE(%s::jsonb,task_json), updated_at=%s::timestamptz WHERE task_id=%s"
        params: tuple[Any, ...] = (status, json.dumps(result) if result is not None else None, error_code,
                                  json.dumps(task) if task is not None else None, updated_at, task_id)
        if expected_status is not None:
            query += " AND status=%s"
            params += (expected_status,)
        with self._connection() as conn:
            cursor = conn.execute(query, params)
            if cursor.rowcount != 1:
                exists = conn.execute("SELECT 1 FROM public.agent_tasks WHERE task_id=%s", (task_id,)).fetchone()
                if exists is None:
                    raise KeyError(f"Unknown task: {task_id}")
                raise ValueError(f"Task state changed before transition to {status}.")

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM public.agent_tasks WHERE task_id=%s", (task_id,)).fetchone()
        return self._record(row)

    def list(self, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with self._connection() as conn:
            if status:
                rows = conn.execute("SELECT * FROM public.agent_tasks WHERE status=%s ORDER BY created_at DESC LIMIT %s", (status, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM public.agent_tasks ORDER BY created_at DESC LIMIT %s", (limit,)).fetchall()
        return [self._record(row) for row in rows]
