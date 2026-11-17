"""FP118: task due time + alerts.

A task can now carry a due time as well as a due date, and tasks
with both alert: cron-job.org POSTs /api/automation/tasks/due
every 15 minutes, and the route pushes one notification per due
task through a second MacroDroid webhook macro. A task alerts
once (alerted_at), rescheduling re-arms it, and a date-only task
never alerts — it has no moment to fire at.
"""

import re
import shutil
import subprocess
import sys
import tempfile
import types
from contextlib import contextmanager
from datetime import date, datetime, time
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

import main
from tasks_store import PostgresTaskStore

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "index.html"
RENDER_YAML = ROOT / "render.yaml"

PIN = "test-pin-1234"
SECRET = "test-session-secret-0123456789abcdef"
CRON_TOKEN = "test-cron-token"
URL = "postgresql://user:pass@db.example.com:5432/postgres"
WEBHOOK = "https://macrodroid.example.com/task-webhook"
LONDON = ZoneInfo("Europe/London")

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


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class _AlertFakeStore:
    """In-memory stand-in for the task store, with alerting."""

    def __init__(self, due=()):
        self.tasks = {}
        self.next_id = 1
        self._due = list(due)
        self.marked = []

    def list_tasks(self):
        return list(self.tasks.values())

    def add_task(self, title, notes="", due_date=None, due_time=None):
        task_id = self.next_id
        self.next_id += 1
        task = {
            "id": task_id, "title": title, "notes": notes,
            "due_date": due_date, "due_time": due_time, "done": False,
            "created_at": "2026-11-17 13:45:00",
            "updated_at": "2026-11-17 13:45:00",
            "alerted_at": None,
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

    def due_tasks(self, *args, **kwargs):
        return list(self._due)

    def mark_alerted(self, task_id):
        self.marked.append(task_id)
        if task_id in self.tasks:
            self.tasks[task_id]["alerted_at"] = "2026-11-17 20:00:00"
        return True


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


def _row(task_id=1, due=None, due_time=None, done=False, alerted=None):
    return (
        task_id, "Title", "Notes", due or date(2026, 11, 20),
        time(9, 0) if due_time is None else due_time, done,
        datetime(2026, 11, 17, 13, 45, 30), datetime(2026, 11, 17, 13, 45, 30),
        alerted,
    )


def _due_task(task_id, title):
    return {
        "id": task_id, "title": title, "notes": "",
        "due_date": "2026-11-17", "due_time": "20:05", "done": False,
        "created_at": "2026-11-17 13:45:00",
        "updated_at": "2026-11-17 13:45:00", "alerted_at": None,
    }


# --- store ---


def test_task_row_normalises_due_time_and_alerted_at(fake_psycopg):
    store = PostgresTaskStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = [
            _row(1, due_time=time(9, 30), alerted=datetime(2026, 11, 17, 9, 0, 0))
        ]
        return conn

    fake_psycopg.connect = connect
    task = store.list_tasks()[0]
    assert task["due_time"] == "09:30"
    assert task["alerted_at"] == "2026-11-17 09:00:00"


def test_due_tasks_window(fake_psycopg):
    store = PostgresTaskStore(URL)
    day = date(2026, 11, 17)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = [
            _row(1, due=day, due_time=time(12, 10)),  # due in 10 min: in
            _row(2, due=day, due_time=time(13, 0)),   # due in an hour: out
            _row(3, due=day, due_time=time(11, 30)),  # due 30 min ago: in (grace)
            _row(4, due=day, due_time=time(10, 0)),   # due 2 hours ago: out
        ]
        return conn

    fake_psycopg.connect = connect
    now = datetime(2026, 11, 17, 12, 0, tzinfo=LONDON)
    assert [t["id"] for t in store.due_tasks(now=now)] == [1, 3]


def test_due_tasks_sql_filters_undone_timed_unalerted(fake_psycopg):
    store = PostgresTaskStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = []
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    store.due_tasks(now=datetime(2026, 11, 17, 12, 0, tzinfo=LONDON))
    sql, _ = conn_holder["conn"].executed[0]
    assert "done = FALSE" in sql
    assert "due_date IS NOT NULL" in sql
    assert "due_time IS NOT NULL" in sql
    assert "alerted_at IS NULL" in sql


def test_due_tasks_accepts_naive_now(fake_psycopg):
    store = PostgresTaskStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = [_row(1, due=date(2026, 11, 17), due_time=time(12, 10))]
        return conn

    fake_psycopg.connect = connect
    assert [t["id"] for t in store.due_tasks(now=datetime(2026, 11, 17, 12, 0))] == [1]


def test_due_tasks_limit(fake_psycopg):
    store = PostgresTaskStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = [
            _row(1, due=date(2026, 11, 17), due_time=time(12, 5)),
            _row(2, due=date(2026, 11, 17), due_time=time(12, 6)),
            _row(3, due=date(2026, 11, 17), due_time=time(12, 7)),
        ]
        return conn

    fake_psycopg.connect = connect
    now = datetime(2026, 11, 17, 12, 0, tzinfo=LONDON)
    assert len(store.due_tasks(now=now, limit=2)) == 2


def test_mark_alerted_updates_and_returns_bool(fake_psycopg):
    store = PostgresTaskStore(URL)
    conn_holder = {}

    def connect_present(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (3,)
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect_present
    assert store.mark_alerted(3) is True
    sql, params = conn_holder["conn"].executed[0]
    assert "SET alerted_at = now()" in sql
    assert params == (3,)

    def connect_absent(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = None
        return conn

    fake_psycopg.connect = connect_absent
    assert store.mark_alerted(99) is False


def test_update_task_allows_due_time_and_alerted_at(fake_psycopg):
    store = PostgresTaskStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = _row(1, due_time=time(10, 0))
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    updated = store.update_task(1, due_time="10:00", alerted_at=None)
    assert updated["due_time"] == "10:00"
    sql, params = conn_holder["conn"].executed[0]
    assert "SET due_time = %s, alerted_at = %s, updated_at = now()" in sql
    assert params == ("10:00", None, 1)


# --- routes: due time on tasks ---


def test_add_task_accepts_due_time_and_normalises(monkeypatch):
    client = _authed_client(monkeypatch)
    store = _AlertFakeStore()
    with patch.object(main, "task_store_or_none", return_value=store):
        res = client.post("/api/tasks", json={
            "title": "Call bank", "due_date": "2026-11-18", "due_time": "9:30",
        })
    assert res.status_code == 200
    assert store.tasks[1]["due_time"] == "09:30"


def test_add_task_rejects_bad_due_time(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch.object(main, "task_store_or_none", return_value=_AlertFakeStore()):
        assert client.post("/api/tasks", json={"title": "T", "due_time": "25:00"}).status_code == 400
        assert client.post("/api/tasks", json={"title": "T", "due_time": "half past"}).status_code == 400


def test_update_task_reschedule_rearms_alert(monkeypatch):
    client = _authed_client(monkeypatch)
    store = _AlertFakeStore()
    store.add_task("Call bank")
    store.tasks[1]["alerted_at"] = "2026-11-17 09:00:00"
    with patch.object(main, "task_store_or_none", return_value=store):
        res = client.put("/api/tasks/1", json={"due_date": "2026-11-19", "due_time": "10:00"})
    assert res.status_code == 200
    assert store.tasks[1]["due_date"] == "2026-11-19"
    assert store.tasks[1]["due_time"] == "10:00"
    assert store.tasks[1]["alerted_at"] is None


def test_update_task_done_toggle_does_not_rearm(monkeypatch):
    client = _authed_client(monkeypatch)
    store = _AlertFakeStore()
    store.add_task("Call bank")
    store.tasks[1]["alerted_at"] = "2026-11-17 09:00:00"
    with patch.object(main, "task_store_or_none", return_value=store):
        res = client.put("/api/tasks/1", json={"done": True})
    assert res.status_code == 200
    assert store.tasks[1]["alerted_at"] == "2026-11-17 09:00:00"


# --- routes: the due-check endpoint ---


def _due_client(monkeypatch):
    monkeypatch.setenv("KAIVOR_CRON_TOKEN", CRON_TOKEN)
    return main.app.test_client()


def test_due_endpoint_requires_cron_token(monkeypatch):
    client = _due_client(monkeypatch)
    with patch.object(main, "task_store_or_none", return_value=_AlertFakeStore()):
        assert client.post("/api/automation/tasks/due").status_code == 401


def test_due_endpoint_not_configured_without_store(monkeypatch):
    client = _due_client(monkeypatch)
    monkeypatch.setenv("KAIVOR_MACRODROID_TASK_WEBHOOK_URL", WEBHOOK)
    with patch.object(main, "task_store_or_none", return_value=None):
        res = client.post(f"/api/automation/tasks/due?token={CRON_TOKEN}")
    assert res.status_code == 503


def test_due_endpoint_not_configured_without_webhook(monkeypatch):
    client = _due_client(monkeypatch)
    monkeypatch.delenv("KAIVOR_MACRODROID_TASK_WEBHOOK_URL", raising=False)
    with patch.object(main, "task_store_or_none", return_value=_AlertFakeStore()):
        res = client.post(f"/api/automation/tasks/due?token={CRON_TOKEN}")
    assert res.status_code == 503


def test_due_endpoint_quiet_when_nothing_due(monkeypatch):
    client = _due_client(monkeypatch)
    monkeypatch.setenv("KAIVOR_MACRODROID_TASK_WEBHOOK_URL", WEBHOOK)
    with patch.object(main, "task_store_or_none", return_value=_AlertFakeStore()):
        with patch("requests.post") as post:
            res = client.post(f"/api/automation/tasks/due?token={CRON_TOKEN}")
    assert res.status_code == 200
    assert res.json == {"success": True, "alerted": [], "count": 0}
    post.assert_not_called()


def test_due_endpoint_alerts_and_marks(monkeypatch):
    client = _due_client(monkeypatch)
    monkeypatch.setenv("KAIVOR_MACRODROID_TASK_WEBHOOK_URL", WEBHOOK)
    store = _AlertFakeStore(due=[_due_task(1, "Call bank")])
    with patch.object(main, "task_store_or_none", return_value=store):
        with patch("requests.post", return_value=_FakeResponse(200)) as post:
            res = client.post(f"/api/automation/tasks/due?token={CRON_TOKEN}")
    assert res.status_code == 200
    assert res.json == {"success": True, "alerted": ["Call bank"], "count": 1}
    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == WEBHOOK
    assert b"Call bank" in kwargs["data"]
    assert b"2026-11-17 20:05" in kwargs["data"]
    assert store.marked == [1]


def test_due_endpoint_webhook_failure_does_not_mark(monkeypatch):
    client = _due_client(monkeypatch)
    monkeypatch.setenv("KAIVOR_MACRODROID_TASK_WEBHOOK_URL", WEBHOOK)
    store = _AlertFakeStore(due=[_due_task(1, "Call bank")])
    with patch.object(main, "task_store_or_none", return_value=store):
        with patch("requests.post", return_value=_FakeResponse(500)):
            res = client.post(f"/api/automation/tasks/due?token={CRON_TOKEN}")
    assert res.status_code == 502
    assert res.json["alerted"] == []
    assert store.marked == []


def test_due_endpoint_caps_at_five(monkeypatch):
    client = _due_client(monkeypatch)
    monkeypatch.setenv("KAIVOR_MACRODROID_TASK_WEBHOOK_URL", WEBHOOK)
    due = [_due_task(i, f"Task {i}") for i in range(1, 7)]
    store = _AlertFakeStore(due=due)
    with patch.object(main, "task_store_or_none", return_value=store):
        with patch("requests.post", return_value=_FakeResponse(200)) as post:
            res = client.post(f"/api/automation/tasks/due?token={CRON_TOKEN}")
    assert res.status_code == 200
    assert res.json["count"] == 5
    assert post.call_count == 5
    assert store.marked == [1, 2, 3, 4, 5]


# --- template + config ---


def test_task_form_has_time_input():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="task-time"' in html
    assert "Due time (optional" in html
    assert "due_time: timeInput.value || null" in html
    assert ".task-due-overdue { color:var(--red); }" in html


def test_task_overdue_node():
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    html = TEMPLATE.read_text(encoding="utf-8")
    row_match = re.search(r"function taskRowHtml\(task\) \{(.*?)\n\}", html, re.S)
    due_text_match = re.search(r"function taskDueText\(task\) \{(.*?)\n\}", html, re.S)
    overdue_match = re.search(r"function taskIsOverdue\(task\) \{(.*?)\n\}", html, re.S)
    esc_match = re.search(r"function escapeHtml\(value\) \{(.*?)\n\}", html, re.S)
    assert row_match is not None
    assert due_text_match is not None
    assert overdue_match is not None
    assert esc_match is not None
    script = (
        "import assert from 'node:assert/strict';\n"
        + NODE_PREAMBLE
        + esc_match.group(0)
        + "\n"
        + due_text_match.group(0)
        + "\n"
        + overdue_match.group(0)
        + "\n"
        + row_match.group(0)
        + "\nassert.strictEqual(taskDueText({due_date: '2026-11-18', due_time: '09:30'}), 'Due 2026-11-18 09:30');\n"
        + "assert.strictEqual(taskDueText({due_date: '2026-11-18', due_time: null}), 'Due 2026-11-18');\n"
        + "assert.strictEqual(taskDueText({due_date: null}), '');\n"
        + "assert.strictEqual(taskIsOverdue({due_date: '2020-01-01', due_time: '09:00'}), true);\n"
        + "assert.strictEqual(taskIsOverdue({due_date: '2099-01-01', due_time: '09:00'}), false);\n"
        + "assert.strictEqual(taskIsOverdue({due_date: null}), false);\n"
        + "const overdue = taskRowHtml({id: 1, title: 'Late', due_date: '2020-01-01', due_time: '09:00', notes: '', done: false});\n"
        + "assert.ok(overdue.includes('task-due-overdue'));\n"
        + "assert.ok(overdue.includes('Due 2020-01-01 09:00'));\n"
        + "const doneLate = taskRowHtml({id: 2, title: 'Late but done', due_date: '2020-01-01', due_time: '09:00', notes: '', done: true});\n"
        + "assert.ok(!doneLate.includes('task-due-overdue'));\n"
        + "const future = taskRowHtml({id: 3, title: 'Later', due_date: '2099-06-01', due_time: null, notes: '', done: false});\n"
        + "assert.ok(future.includes('Due 2099-06-01'));\n"
        + "assert.ok(!future.includes('task-due-overdue'));\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        result = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        Path(path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr


def test_render_yaml_has_task_webhook_var():
    text = RENDER_YAML.read_text(encoding="utf-8")
    assert "KAIVOR_MACRODROID_TASK_WEBHOOK_URL" in text
