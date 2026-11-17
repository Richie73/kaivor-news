"""FP114: in-app tasks — a Tasks view in the Hub, backed by the
public.tasks table in Postgres (same database as memories). Tasks
are Postgres-only: without a database URL the routes report not
configured instead of inventing a store."""

import re
import shutil
import subprocess
import sys
import tempfile
import types
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import main
from tasks_store import PostgresTaskStore, task_store_or_none

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

PIN = "test-pin-1234"
SECRET = "test-session-secret-0123456789abcdef"
URL = "postgresql://user:pass@db.example.com:5432/postgres"

# escapeHtml builds a div in the browser; the node stub below mimics
# the escaping a text node gets when serialised (&, <, >).
NODE_PREAMBLE = """
const document = { createElement: () => { let raw = ''; return {
    set textContent(v) { raw = String(v ?? ''); },
    get innerHTML() { return raw.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
}; } };
"""


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


class _FakeStore:
    """In-memory stand-in for the Postgres task store."""

    def __init__(self):
        self.tasks = {}
        self.next_id = 1

    def list_tasks(self):
        return list(self.tasks.values())

    def add_task(self, title, notes="", due_date=None):
        task_id = self.next_id
        self.next_id += 1
        task = {
            "id": task_id, "title": title, "notes": notes,
            "due_date": due_date, "done": False,
            "created_at": "2026-11-17 13:45:00",
            "updated_at": "2026-11-17 13:45:00",
        }
        self.tasks[task_id] = task
        return task_id

    def update_task(self, task_id, **fields):
        task = self.tasks.get(task_id)
        if task is None:
            return None
        task.update(fields)
        return task

    def delete_task(self, task_id):
        return self.tasks.pop(task_id, None) is not None


@pytest.fixture
def fake_psycopg(monkeypatch):
    module = types.ModuleType("psycopg")
    connections = []

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        connections.append(conn)
        return conn

    module.connect = connect
    module.connections = connections
    monkeypatch.setitem(sys.modules, "psycopg", module)
    return module


def _authed_client(monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_PIN", PIN)
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", SECRET)
    client = main.app.test_client()
    with client.session_transaction() as sess:
        sess["reading_authenticated"] = True
    return client


def _locked_client(monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_PIN", PIN)
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", SECRET)
    return main.app.test_client()


def _template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def _row(task_id=1, due=None, done=False):
    return (
        task_id, "Title", "Notes", due or date(2026, 11, 20), done,
        datetime(2026, 11, 17, 13, 45, 30), datetime(2026, 11, 17, 13, 45, 30),
    )


# --- store ---


def test_store_requires_a_url():
    with pytest.raises(ValueError, match="KAIVOR_READING_DATABASE_URL"):
        PostgresTaskStore("")


def test_store_requires_postgresql_scheme():
    with pytest.raises(ValueError, match="postgresql://"):
        PostgresTaskStore("sqlite:///tasks.db")


def test_list_tasks_orders_open_first_and_normalises_dates(fake_psycopg):
    store = PostgresTaskStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = [_row(1), _row(2, done=True)]
        return conn

    fake_psycopg.connect = connect
    tasks = store.list_tasks()
    assert [t["id"] for t in tasks] == [1, 2]
    assert tasks[0]["due_date"] == "2026-11-20"
    assert tasks[0]["created_at"] == "2026-11-17 13:45:30"
    assert tasks[0]["done"] is False


def test_list_tasks_sql_orders_by_done_then_due_date(fake_psycopg):
    store = PostgresTaskStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = []
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    store.list_tasks()
    sql, params = conn_holder["conn"].executed[0]
    assert "FROM public.tasks" in sql
    assert "ORDER BY done ASC, due_date ASC NULLS LAST" in sql


def test_add_task_inserts_and_returns_id(fake_psycopg):
    store = PostgresTaskStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (9,)
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    assert store.add_task("Buy milk", "2 pints", "2026-11-18") == 9
    sql, params = conn_holder["conn"].executed[0]
    assert "INSERT INTO public.tasks" in sql
    assert "RETURNING id" in sql
    assert params == ("Buy milk", "2 pints", "2026-11-18")


def test_update_task_sets_only_given_fields(fake_psycopg):
    store = PostgresTaskStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = _row(1, done=True)
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    updated = store.update_task(1, done=True)
    assert updated["done"] is True
    sql, params = conn_holder["conn"].executed[0]
    assert "UPDATE public.tasks" in sql
    assert "SET done = %s, updated_at = now()" in sql
    assert params == (True, 1)


def test_update_task_with_no_fields_reads_the_task(fake_psycopg):
    store = PostgresTaskStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = _row(1)
        return conn

    fake_psycopg.connect = connect
    assert store.update_task(1)["id"] == 1


def test_update_task_returns_none_when_missing(fake_psycopg):
    store = PostgresTaskStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = None
        return conn

    fake_psycopg.connect = connect
    assert store.update_task(99, done=True) is None


def test_delete_task_returns_whether_a_row_was_removed(fake_psycopg):
    store = PostgresTaskStore(URL)

    def connect_present(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (3,)
        return conn

    fake_psycopg.connect = connect_present
    assert store.delete_task(3) is True

    def connect_absent(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = None
        return conn

    fake_psycopg.connect = connect_absent
    assert store.delete_task(99) is False


def test_store_missing_psycopg_fails_with_install_hint(monkeypatch):
    monkeypatch.setitem(sys.modules, "psycopg", None)
    store = PostgresTaskStore(URL)
    with pytest.raises(RuntimeError, match="requirements-postgres.txt"):
        store.list_tasks()


def test_task_store_or_none(monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_DATABASE_URL", URL)
    assert isinstance(task_store_or_none(), PostgresTaskStore)
    monkeypatch.delenv("KAIVOR_READING_DATABASE_URL", raising=False)
    assert task_store_or_none() is None


# --- routes ---


def test_get_tasks_locked(monkeypatch):
    client = _locked_client(monkeypatch)
    with patch.object(main, "task_store_or_none", return_value=_FakeStore()):
        assert client.get("/api/tasks").status_code == 401


def test_get_tasks_returns_list(monkeypatch):
    client = _authed_client(monkeypatch)
    store = _FakeStore()
    store.add_task("Buy milk")
    with patch.object(main, "task_store_or_none", return_value=store):
        res = client.get("/api/tasks")
    assert res.status_code == 200
    assert res.json["tasks"][0]["title"] == "Buy milk"


def test_get_tasks_not_configured(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch.object(main, "task_store_or_none", return_value=None):
        res = client.get("/api/tasks")
    assert res.status_code == 503
    assert res.json["success"] is False


def test_add_task_creates(monkeypatch):
    client = _authed_client(monkeypatch)
    store = _FakeStore()
    with patch.object(main, "task_store_or_none", return_value=store):
        res = client.post("/api/tasks", json={
            "title": "Buy milk", "notes": "2 pints", "due_date": "2026-11-18",
        })
    assert res.status_code == 200
    assert res.json["id"] == 1
    assert store.tasks[1]["due_date"] == "2026-11-18"


def test_add_task_requires_title(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch.object(main, "task_store_or_none", return_value=_FakeStore()):
        res = client.post("/api/tasks", json={"title": "  "})
    assert res.status_code == 400


def test_add_task_rejects_long_title(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch.object(main, "task_store_or_none", return_value=_FakeStore()):
        res = client.post("/api/tasks", json={"title": "x" * 201})
    assert res.status_code == 400


def test_add_task_rejects_bad_due_date(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch.object(main, "task_store_or_none", return_value=_FakeStore()):
        res = client.post("/api/tasks", json={"title": "T", "due_date": "18/11/2026"})
    assert res.status_code == 400


def test_add_task_not_configured(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch.object(main, "task_store_or_none", return_value=None):
        res = client.post("/api/tasks", json={"title": "T"})
    assert res.status_code == 503


def test_update_task_toggles_done(monkeypatch):
    client = _authed_client(monkeypatch)
    store = _FakeStore()
    store.add_task("Buy milk")
    with patch.object(main, "task_store_or_none", return_value=store):
        res = client.put("/api/tasks/1", json={"done": True})
    assert res.status_code == 200
    assert res.json["task"]["done"] is True


def test_update_task_not_found(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch.object(main, "task_store_or_none", return_value=_FakeStore()):
        res = client.put("/api/tasks/99", json={"done": True})
    assert res.status_code == 404


def test_update_task_rejects_bad_due_date(monkeypatch):
    client = _authed_client(monkeypatch)
    store = _FakeStore()
    store.add_task("Buy milk")
    with patch.object(main, "task_store_or_none", return_value=store):
        res = client.put("/api/tasks/1", json={"due_date": "tomorrow"})
    assert res.status_code == 400


def test_delete_task(monkeypatch):
    client = _authed_client(monkeypatch)
    store = _FakeStore()
    store.add_task("Buy milk")
    with patch.object(main, "task_store_or_none", return_value=store):
        res = client.delete("/api/tasks/1")
    assert res.status_code == 200
    assert store.tasks == {}


def test_delete_task_not_found(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch.object(main, "task_store_or_none", return_value=_FakeStore()):
        res = client.delete("/api/tasks/99")
    assert res.status_code == 404


# --- template ---


def test_tasks_button_and_view_markup():
    html = _template_text()
    assert 'onclick="showTasks()">✅ Tasks</button>' in html
    assert 'id="task-title"' in html
    assert 'id="task-due"' in html
    assert 'id="task-notes"' in html
    assert 'id="tasks-list"' in html
    assert "function taskRowHtml(task)" in html
    assert "async function loadTasks()" in html
    assert "async function addTask()" in html
    assert "async function toggleTask(id, done, checkbox)" in html
    assert "async function deleteTask(id, button)" in html
    # The three hide calls lead showTasks, in weather -> markets -> hub order.
    start = html.index("async function showTasks() {")
    window = html[start:start + 400]
    assert window.index("hideWeatherView();") < window.index("hideMarketsView();")
    assert window.index("hideMarketsView();") < window.index("hideMorningHubView();")


def test_task_row_html_node():
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    html = _template_text()
    row_match = re.search(r"function taskRowHtml\(task\) \{(.*?)\n\}", html, re.S)
    esc_match = re.search(r"function escapeHtml\(value\) \{(.*?)\n\}", html, re.S)
    assert row_match is not None
    assert esc_match is not None
    script = (
        "import assert from 'node:assert/strict';\n"
        + NODE_PREAMBLE
        + esc_match.group(0)
        + "\n"
        + row_match.group(0)
        + "\nconst open = taskRowHtml({id: 1, title: 'Buy <milk>', due_date: '2026-11-18', notes: '2 pints', done: false});\n"
        + "assert.ok(open.includes('Buy &lt;milk&gt;'));\n"
        + "assert.ok(open.includes('Due 2026-11-18'));\n"
        + "assert.ok(open.includes('2 pints'));\n"
        + "assert.ok(!open.includes(' checked '));\n"
        + "assert.ok(!open.includes('task-done'));\n"
        + "const done = taskRowHtml({id: 2, title: 'Done thing', due_date: null, notes: '', done: true});\n"
        + "assert.ok(done.includes(' checked '));\n"
        + "assert.ok(done.includes('task-done'));\n"
        + "assert.ok(!done.includes('Due '));\n"
        + "assert.ok(!done.includes('article-description'));\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        result = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        Path(path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr
