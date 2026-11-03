"""SQLite persistence for delegated agent tasks and their results."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class AgentTaskStore:
    def __init__(self, database_path: str | Path = "data/agent_tasks.db") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialise(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS agent_tasks (
                    task_id TEXT PRIMARY KEY,
                    assigned_to TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    task_json TEXT NOT NULL,
                    result_json TEXT,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_tasks_status_created "
                "ON agent_tasks(status, created_at DESC)"
            )

    def create(self, task: dict[str, Any], status: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO agent_tasks
                (task_id, assigned_to, task_type, status, task_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (task["task_id"], task["assigned_to"], task["task_type"], status,
                 json.dumps(task, ensure_ascii=False), task["created_at"], task["created_at"]),
            )

    def update(
        self, task_id: str, status: str, *, result: dict[str, Any] | None = None,
        error_code: str | None = None, task: dict[str, Any] | None = None, updated_at: str,
        expected_status: str | None = None,
    ) -> None:
        query = (
            "UPDATE agent_tasks SET status = ?, result_json = ?, error_code = ?, "
            "task_json = COALESCE(?, task_json), updated_at = ? WHERE task_id = ?"
        )
        values = (status, json.dumps(result, ensure_ascii=False) if result is not None else None,
                  error_code, json.dumps(task, ensure_ascii=False) if task is not None else None,
                  updated_at, task_id)
        if expected_status is not None:
            query += " AND status = ?"
            values += (expected_status,)
        with self._connection() as connection:
            cursor = connection.execute(query, values)
            if cursor.rowcount != 1:
                exists = connection.execute(
                    "SELECT 1 FROM agent_tasks WHERE task_id = ?", (task_id,)
                ).fetchone()
                if exists is None:
                    raise KeyError(f"Unknown task: {task_id}")
                raise ValueError(f"Task state changed before transition to {status}.")

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM agent_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list(self, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with self._connection() as connection:
            if status:
                rows = connection.execute(
                    "SELECT * FROM agent_tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM agent_tasks ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "task_id": row["task_id"],
            "assigned_to": row["assigned_to"],
            "task_type": row["task_type"],
            "status": row["status"],
            "task": json.loads(row["task_json"]),
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error_code": row["error_code"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
