"""FP121: today's tasks in the Hub and the morning brief.

The Hub gains a "Tasks today" card (open tasks due today or
overdue, tickable in place), and the 06:00 brief lists the same
tasks in a "Tasks today:" section. The brief side is pure
Python (brief_task_lines + build_morning_brief); the Hub side
fetches /api/tasks like the calendar card fetches its feed.
"""

import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from morning_brief import brief_task_lines, build_morning_brief, format_brief_text

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"
LONDON = ZoneInfo("Europe/London")
MONDAY_7AM = datetime(2026, 11, 16, 7, 0, tzinfo=LONDON)

TASKS = [
    {"id": 1, "title": "Ring the hire shop", "due_date": "2026-11-16", "due_time": "09:30", "done": False},
    {"id": 2, "title": "Buy milk", "due_date": "2026-11-16", "due_time": None, "done": False},
    {"id": 3, "title": "Overdue invoice", "due_date": "2026-11-14", "due_time": None, "done": False},
    {"id": 4, "title": "Done already", "due_date": "2026-11-16", "due_time": None, "done": True},
    {"id": 5, "title": "No date", "due_date": None, "due_time": None, "done": False},
    {"id": 6, "title": "Next week", "due_date": "2026-11-23", "due_time": None, "done": False},
]


def test_brief_task_lines_today_overdue_and_done():
    lines = brief_task_lines(TASKS, "2026-11-16")
    assert lines == [
        "Ring the hire shop \u2014 due 09:30",
        "Buy milk \u2014 due today",
        "Overdue invoice \u2014 overdue (due 2026-11-14)",
    ]


def test_brief_task_lines_empty_inputs():
    assert brief_task_lines([], "2026-11-16") == []
    assert brief_task_lines(None, "2026-11-16") == []
    assert brief_task_lines(TASKS, "2026-11-13") == []


def test_brief_task_lines_caps_at_five():
    many = [
        {"id": i, "title": f"Task {i}", "due_date": "2026-11-16", "due_time": None, "done": False}
        for i in range(8)
    ]
    assert len(brief_task_lines(many, "2026-11-16")) == 5


def test_build_morning_brief_includes_tasks():
    brief = build_morning_brief(
        MONDAY_7AM, [], {}, {"status": "error"}, {"rail": {"status": "not_configured"}},
        {"status": "error", "error": "Weather unavailable."}, None, TASKS,
    )
    assert brief["tasks"] == [
        "Ring the hire shop \u2014 due 09:30",
        "Buy milk \u2014 due today",
        "Overdue invoice \u2014 overdue (due 2026-11-14)",
    ]
    text = format_brief_text(brief)
    assert "Tasks today:" in text
    assert "\u2022 Ring the hire shop \u2014 due 09:30" in text


def test_format_brief_text_omits_empty_tasks_section():
    brief = build_morning_brief(
        MONDAY_7AM, [], {}, {"status": "error"}, {"rail": {"status": "not_configured"}},
        {"status": "error", "error": "Weather unavailable."},
    )
    assert brief["tasks"] == []
    assert "Tasks today:" not in format_brief_text(brief)


def test_hub_tasks_card_markup():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="hub-tasks"' in html
    assert "Tasks today" in html
    assert "async function loadMorningHubTasks()" in html
    assert "function tasksDueToday(tasks, todayIso) {" in html
    assert "function hubTaskRowHtml(task, todayIso) {" in html
    start = html.index("function renderMorningHub() {")
    window = html[start:start + 2000]
    assert "loadMorningHubTasks();" in window


def test_hub_tasks_helpers_node():
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    html = TEMPLATE.read_text(encoding="utf-8")
    due_match = re.search(r"function tasksDueToday\(tasks, todayIso\) \{(.*?)\n\}", html, re.S)
    row_match = re.search(r"function hubTaskRowHtml\(task, todayIso\) \{(.*?)\n\}", html, re.S)
    escape_match = re.search(r"function escapeHtml\(value\) \{(.*?)\n\}", html, re.S)
    assert due_match is not None
    assert row_match is not None
    assert escape_match is not None
    script = (
        "import assert from 'node:assert/strict';\n"
        "const document = {createElement: () => ({textContent: '', get innerHTML() { return this.textContent; }})};\n"
        + escape_match.group(0)
        + "\n"
        + due_match.group(0)
        + "\n"
        + row_match.group(0)
        + "\nconst tasks = [\n"
        + "  {id: 1, title: 'Late one', due_date: '2026-11-16', due_time: '14:00', done: false},\n"
        + "  {id: 2, title: 'Early one', due_date: '2026-11-16', due_time: '08:00', done: false},\n"
        + "  {id: 3, title: 'Overdue one', due_date: '2026-11-14', due_time: null, done: false},\n"
        + "  {id: 4, title: 'Done one', due_date: '2026-11-16', due_time: null, done: true},\n"
        + "  {id: 5, title: 'Future one', due_date: '2026-11-20', due_time: null, done: false},\n"
        + "  {id: 6, title: 'Undated one', due_date: null, due_time: null, done: false},\n"
        + "];\n"
        + "const due = tasksDueToday(tasks, '2026-11-16');\n"
        + "assert.deepStrictEqual(due.map(t => t.id), [3, 2, 1]);\n"
        + "const row = hubTaskRowHtml({id: 3, title: 'Overdue one', due_date: '2026-11-14', due_time: null}, '2026-11-16');\n"
        + "assert.ok(row.includes('task-due-overdue'));\n"
        + "assert.ok(row.includes('Overdue'));\n"
        + "assert.ok(row.includes('toggleTask(3, this.checked, this)'));\n"
        + "const timed = hubTaskRowHtml({id: 2, title: 'Early one', due_date: '2026-11-16', due_time: '08:00'}, '2026-11-16');\n"
        + "assert.ok(timed.includes('08:00'));\n"
        + "assert.ok(!timed.includes('task-due-overdue'));\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        result = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        Path(path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr
