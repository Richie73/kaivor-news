"""FP113: memories live in Postgres (Supabase) when a database URL is
configured, so they survive redeploys. SQLite stays the fallback for
local runs and Termux, where psycopg has no wheel."""

import sqlite3
import sys
import types
from contextlib import contextmanager
from datetime import datetime

import pytest

from core.memory import api as memory_api
from core.memory import database as memory_db
from core.memory.manager import MemoryManager
from core.memory.postgres_store import PostgresMemoryStore

URL = "postgresql://user:pass@db.example.com:5432/postgres"


class _FakeCursor:
    def __init__(self, conn):
        self._conn = conn

    def fetchone(self):
        return self._conn.fetchone_result

    def fetchall(self):
        return self._conn.fetchall_result


class _FakeConnection:
    def __init__(self):
        self.executed = []
        self.closed = False
        self.fetchone_result = None
        self.fetchall_result = []

    def execute(self, sql, params=()):
        self.executed.append((sql, params))
        return _FakeCursor(self)

    @contextmanager
    def transaction(self):
        yield self

    def close(self):
        self.closed = True


@pytest.fixture
def fake_psycopg(monkeypatch):
    """Stand in for the real psycopg module; records every connect."""
    module = types.ModuleType("psycopg")
    connections = []

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.connect_kwargs = kwargs
        conn.connect_url = database_url
        connections.append(conn)
        return conn

    module.connect = connect
    module.connections = connections
    monkeypatch.setitem(sys.modules, "psycopg", module)
    return module


@pytest.fixture
def tmp_memory_db(monkeypatch, tmp_path):
    db_path = tmp_path / "mem.db"
    monkeypatch.setattr(memory_db, "DB_PATH", db_path)
    monkeypatch.setattr(memory_api, "_manager", None)
    return db_path


def _row(memory_id=1, created=None):
    return (
        memory_id, "general", "Title", "Content",
        created or datetime(2026, 11, 17, 13, 45, 30),
        3, "manual", "",
    )


# --- URL validation ---


def test_requires_a_url():
    with pytest.raises(ValueError, match="KAIVOR_READING_DATABASE_URL"):
        PostgresMemoryStore("")


def test_requires_postgresql_scheme():
    with pytest.raises(ValueError, match="postgresql://"):
        PostgresMemoryStore("sqlite:///mem.db")


def test_appends_sslmode_when_missing():
    store = PostgresMemoryStore(URL)
    assert store.database_url == URL + "?sslmode=require"
    store = PostgresMemoryStore(URL + "?pooler=true")
    assert store.database_url == URL + "?pooler=true&sslmode=require"
    store = PostgresMemoryStore(URL + "?sslmode=disable")
    assert store.database_url == URL + "?sslmode=disable"


# --- connection + statements ---


def test_connect_uses_pooler_safe_options(fake_psycopg):
    store = PostgresMemoryStore(URL)
    store.get_memories()
    conn = fake_psycopg.connections[0]
    assert conn.connect_url == URL + "?sslmode=require"
    assert conn.connect_kwargs["connect_timeout"] == 10
    assert conn.connect_kwargs["prepare_threshold"] is None
    assert conn.closed is True


def test_add_memory_inserts_and_returns_id(fake_psycopg):
    store = PostgresMemoryStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (7,)
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    memory_id = store.add_memory("general", "T", "C", 4, "manual", "x")
    assert memory_id == 7
    sql, params = conn_holder["conn"].executed[0]
    assert "INSERT INTO public.memories" in sql
    assert "RETURNING id" in sql
    assert params == ("general", "T", "C", 4, "manual", "x")
    assert conn_holder["conn"].closed is True


def test_delete_memory_returns_whether_a_row_was_removed(fake_psycopg):
    store = PostgresMemoryStore(URL)

    def connect_present(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (3,)
        return conn

    fake_psycopg.connect = connect_present
    assert store.delete_memory(3) is True

    def connect_absent(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = None
        return conn

    fake_psycopg.connect = connect_absent
    assert store.delete_memory(99) is False


def test_get_memories_formats_postgres_datetimes(fake_psycopg):
    store = PostgresMemoryStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = [_row(2), _row(1)]
        return conn

    fake_psycopg.connect = connect
    memories = store.get_memories()
    assert [m.id for m in memories] == [2, 1]
    # Same string shape as the SQLite store's CURRENT_TIMESTAMP.
    assert memories[0].created_at == "2026-11-17 13:45:30"
    assert memories[0].title == "Title"


def test_get_memories_by_category_filters(fake_psycopg):
    store = PostgresMemoryStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = []
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    store.get_memories_by_category("chat")
    sql, params = conn_holder["conn"].executed[0]
    assert "WHERE category = %s" in sql
    assert params == ("chat",)


def test_search_memories_uses_ilike(fake_psycopg):
    # Postgres LIKE is case-sensitive; the search must use ILIKE or
    # mixed-case memories would never match.
    store = PostgresMemoryStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = []
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    store.search_memories("Wirral")
    sql, params = conn_holder["conn"].executed[0]
    assert "title ILIKE %s" in sql
    assert "content ILIKE %s" in sql
    assert params == ("%Wirral%", "%Wirral%")


def test_missing_psycopg_fails_with_install_hint(monkeypatch):
    # None in sys.modules makes `import psycopg` raise ImportError.
    monkeypatch.setitem(sys.modules, "psycopg", None)
    store = PostgresMemoryStore(URL)
    with pytest.raises(RuntimeError, match="requirements-postgres.txt"):
        store.get_memories()


# --- backend selection ---


def test_api_uses_postgres_when_url_configured(monkeypatch, fake_psycopg):
    monkeypatch.setenv("KAIVOR_READING_DATABASE_URL", URL)
    monkeypatch.setattr(memory_api, "_manager", None)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (5,)
        fake_psycopg.connections.append(conn)
        return conn

    fake_psycopg.connect = connect
    memory_id = memory_api.remember("general", "T", "C")
    assert memory_id == 5
    assert isinstance(memory_api._manager, PostgresMemoryStore)
    conn = fake_psycopg.connections[0]
    sql, params = conn.executed[0]
    assert "INSERT INTO public.memories" in sql
    assert params == ("general", "T", "C", 3, "manual", "")


def test_api_keeps_sqlite_when_url_absent(monkeypatch, tmp_memory_db):
    monkeypatch.delenv("KAIVOR_READING_DATABASE_URL", raising=False)
    memory_id = memory_api.remember("general", "T", "C")
    assert isinstance(memory_api._manager, MemoryManager)
    conn = sqlite3.connect(tmp_memory_db)
    rows = conn.execute("SELECT title FROM memories").fetchall()
    conn.close()
    assert rows == [("T",)]
    assert memory_id == 1
