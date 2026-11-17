"""FP112: chat memory — the chat recalls saved memories, and the user
saves them with a Remember button or from the Memories view. Nothing
is remembered automatically."""

import re
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import main
from core.memory import api as memory_api
from core.memory import database as memory_db
from core.memory.manager import MemoryManager
from core.memory.models import Memory

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

PIN = "test-pin-1234"
SECRET = "test-session-secret-0123456789abcdef"


@pytest.fixture
def tmp_memory_db(monkeypatch, tmp_path):
    """Point the memory store at a throwaway database."""
    db_path = tmp_path / "mem.db"
    monkeypatch.setattr(memory_db, "DB_PATH", db_path)
    monkeypatch.setattr(memory_api, "_manager", None)
    return db_path


def _authed_client(monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_PIN", PIN)
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", SECRET)
    client = main.app.test_client()
    with client.session_transaction() as sess:
        sess["reading_authenticated"] = True
    return client


def _provider_response(text):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"choices": [{"message": {"content": text}}]}
    return response


def _template_text():
    return TEMPLATE.read_text(encoding="utf-8")


# --- schema + migration ---


def test_init_creates_full_schema(tmp_memory_db):
    memory_db.initialise_database()
    conn = sqlite3.connect(tmp_memory_db)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    conn.close()
    assert columns == {
        "id", "category", "title", "content", "created_at",
        "importance", "source", "tags",
    }


def test_init_migrates_legacy_table(tmp_memory_db):
    conn = sqlite3.connect(tmp_memory_db)
    conn.execute("""
        CREATE TABLE memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        "INSERT INTO memories (category, title, content) VALUES (?, ?, ?)",
        ("general", "Old one", "Kept through the migration."),
    )
    conn.commit()
    conn.close()
    memory_db.initialise_database()
    conn = sqlite3.connect(tmp_memory_db)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    row = conn.execute("SELECT title, importance, source, tags FROM memories").fetchone()
    conn.close()
    assert {"importance", "source", "tags"} <= columns
    assert row == ("Old one", 3, "manual", "")


# --- manager ---


def test_add_get_roundtrip(tmp_memory_db):
    manager = MemoryManager()
    memory_id = manager.add_memory(
        "work", "Scaffold ticket", "IPAF 3a/3b until June 2030.",
        importance=5, source="chat", tags="tickets",
    )
    memories = manager.get_memories()
    assert len(memories) == 1
    memory = memories[0]
    assert memory.id == memory_id
    assert memory.title == "Scaffold ticket"
    assert memory.content == "IPAF 3a/3b until June 2030."
    assert memory.category == "work"
    assert memory.importance == 5
    assert memory.source == "chat"
    assert memory.tags == "tickets"
    assert memory.to_dict()["title"] == "Scaffold ticket"


def test_search_finds_by_keyword(tmp_memory_db):
    manager = MemoryManager()
    manager.add_memory("general", "Van service", "L200 booked in for May.")
    manager.add_memory("general", "Guitar lesson", "Thursdays at seven.")
    found = manager.search_memories("L200")
    assert [m.title for m in found] == ["Van service"]
    assert manager.search_memories("nothing-here") == []


def test_search_is_case_insensitive(tmp_memory_db):
    manager = MemoryManager()
    manager.add_memory("general", "Dentist", "Perfect Smile Hoseside.")
    assert [m.title for m in manager.search_memories("hoseside")] == ["Dentist"]


def test_get_by_category_filters(tmp_memory_db):
    manager = MemoryManager()
    manager.add_memory("work", "Site A", "First.")
    manager.add_memory("home", "Site B", "Second.")
    assert [m.title for m in manager.get_memories_by_category("work")] == ["Site A"]


def test_delete_removes_only_that_memory(tmp_memory_db):
    manager = MemoryManager()
    first = manager.add_memory("general", "Keep", "Stays.")
    second = manager.add_memory("general", "Drop", "Goes.")
    assert manager.delete_memory(second) is True
    assert manager.delete_memory(second) is False
    assert [m.id for m in manager.get_memories()] == [first]


def test_from_row_tolerates_five_columns():
    memory = Memory.from_row((7, "general", "Old", "Body", "2026-01-01 00:00:00"))
    assert memory.id == 7
    assert memory.importance == 3
    assert memory.source == "manual"
    assert memory.tags == ""


# --- recall helper ---


def test_recall_empty_question(tmp_memory_db):
    assert main.memory_context_for_chat("") == ("", 0)
    assert main.memory_context_for_chat(None) == ("", 0)


def test_recall_no_memories(tmp_memory_db):
    assert main.memory_context_for_chat("What about the scaffold?") == ("", 0)


def test_recall_matches_keyword(tmp_memory_db):
    MemoryManager().add_memory(
        "work", "Scaffold ticket", "IPAF 3a/3b until June 2030."
    )
    block, count = main.memory_context_for_chat("When does my scaffold ticket run out?")
    assert count == 1
    assert "Scaffold ticket" in block
    assert "June 2030" in block


def test_recall_ignores_stopwords_and_short_words(tmp_memory_db):
    MemoryManager().add_memory("general", "Dentist", "Perfect Smile Hoseside.")
    # Every word here is a stopword or under four letters: no keywords,
    # so nothing is searched even though a memory exists.
    assert main.memory_context_for_chat("what is it") == ("", 0)


def test_recall_caps_at_five(tmp_memory_db):
    manager = MemoryManager()
    for i in range(6):
        manager.add_memory("general", f"Scaffold note {i}", "Scaffold detail.")
    block, count = main.memory_context_for_chat("Tell me about the scaffold.")
    assert count == 5
    assert block.count("Scaffold note") == 5


def test_recall_truncates_long_content(tmp_memory_db):
    MemoryManager().add_memory("general", "Long one", "x" * 500 + " scaffold")
    block, count = main.memory_context_for_chat("scaffold")
    assert count == 1
    assert block.endswith("…")
    assert len(block) < 500


def test_recall_survives_store_failure(monkeypatch, tmp_memory_db):
    monkeypatch.setattr(
        memory_api, "search", Mock(side_effect=RuntimeError("store down"))
    )
    assert main.memory_context_for_chat("scaffold") == ("", 0)


# --- routes ---


def test_get_memories_locked(monkeypatch, tmp_memory_db):
    monkeypatch.setenv("KAIVOR_READING_PIN", PIN)
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", SECRET)
    client = main.app.test_client()
    assert client.get("/api/memories").status_code == 401


def test_get_memories_lists_newest_first(monkeypatch, tmp_memory_db):
    client = _authed_client(monkeypatch)
    manager = MemoryManager()
    manager.add_memory("general", "First", "One.")
    manager.add_memory("general", "Second", "Two.")
    response = client.get("/api/memories")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert [m["title"] for m in payload["memories"]] == ["Second", "First"]


def test_post_memories_creates(monkeypatch, tmp_memory_db):
    client = _authed_client(monkeypatch)
    response = client.post(
        "/api/memories",
        json={"title": "Van", "content": "L200 service in May.", "category": "work"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert isinstance(payload["id"], int)
    listed = client.get("/api/memories").get_json()["memories"]
    assert [m["title"] for m in listed] == ["Van"]


def test_post_memories_validates(monkeypatch, tmp_memory_db):
    client = _authed_client(monkeypatch)
    assert client.post("/api/memories", json={"title": "No body"}).status_code == 400
    assert client.post("/api/memories", json={"content": "No title"}).status_code == 400
    assert client.post(
        "/api/memories", json={"title": "x" * 201, "content": "Too long."}
    ).status_code == 400
    assert client.post(
        "/api/memories", json={"title": "Too long.", "content": "x" * 4001}
    ).status_code == 400


def test_post_memories_locked(monkeypatch, tmp_memory_db):
    monkeypatch.setenv("KAIVOR_READING_PIN", PIN)
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", SECRET)
    client = main.app.test_client()
    response = client.post(
        "/api/memories", json={"title": "Van", "content": "L200 service."}
    )
    assert response.status_code == 401


def test_delete_memories_removes(monkeypatch, tmp_memory_db):
    client = _authed_client(monkeypatch)
    memory_id = MemoryManager().add_memory("general", "Drop", "Goes.")
    assert client.delete(f"/api/memories/{memory_id}").status_code == 200
    assert client.get("/api/memories").get_json()["memories"] == []
    assert client.delete(f"/api/memories/{memory_id}").status_code == 404


def test_chat_recalls_matching_memory(monkeypatch, tmp_memory_db):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    MemoryManager().add_memory(
        "work", "Scaffold ticket", "IPAF 3a/3b until June 2030."
    )
    with patch.object(main.requests, "post", return_value=_provider_response("June 2030.")) as post:
        response = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "When does my scaffold ticket run out?"}]},
        )
    assert response.status_code == 200
    sent = post.call_args.kwargs["json"]
    system = sent["messages"][0]["content"]
    assert "Scaffold ticket" in system
    assert "June 2030" in system


# --- template ---


def test_remember_button_on_assistant_messages():
    html = _template_text()
    assert "function chatMessageHtml(message, index) {" in html
    assert "rememberChatMessage(${index}, this)" in html
    assert "chat-remember-btn" in html
    # User messages return before the button is added.
    body_start = html.index("function chatMessageHtml(message, index) {")
    body = html[body_start:html.index("function renderChatLog()", body_start)]
    assert "if (message.role === 'user') return" in body


def test_remember_posts_to_memories_route():
    html = _template_text()
    assert "function rememberChatMessage(index, button) {" in html
    assert "fetch('/api/memories', {" in html
    assert "category: 'chat', source: 'chat'" in html


def test_memories_view_markup():
    html = _template_text()
    assert "async function showMemories() {" in html
    start = html.index("async function showMemories() {")
    window = html[start:start + 400]
    assert window.index("hideWeatherView();") < window.index("hideMarketsView();")
    assert window.index("hideMarketsView();") < window.index("hideMorningHubView();")
    assert "cacheNewsContainer();" in window
    assert 'id="memory-title"' in html
    assert 'id="memory-content"' in html
    assert 'id="memories-list"' in html
    assert "function loadMemories() {" in html
    assert "function deleteMemory(id, button) {" in html
    assert "fetch('/api/memories/' + id, {method: 'DELETE'})" in html
    assert "Unlock Reading to see your memories." in html


def test_chat_card_links_memories():
    html = _template_text()
    start = html.index("function showChat(element) {")
    body = html[start:html.index("function saveChatWebToggle()", start)]
    assert 'onclick="showMemories()"' in body


def test_refresh_button_hides_in_memories_view():
    html = _template_text()
    assert "Receipts, RAMS, Memories" in html


# --- memoryTitleFor (node) ---


def test_memory_title_for_node():
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    html = _template_text()
    match = re.search(r"function memoryTitleFor\(text\) \{(.*?)\n\}", html, re.S)
    assert match is not None
    script = (
        "import assert from 'node:assert/strict';\n"
        + match.group(0)
        + "\nassert.strictEqual(memoryTitleFor('Hello there'), 'Hello there');\n"
        + "assert.strictEqual(memoryTitleFor('## Big heading\\nMore text'), 'Big heading');\n"
        + "assert.strictEqual(memoryTitleFor('\\n\\n  \\nFirst real line'), 'First real line');\n"
        + "assert.strictEqual(memoryTitleFor(''), 'Chat memory');\n"
        + "const long = memoryTitleFor('x'.repeat(100));\n"
        + "assert.strictEqual(long.length, 60);\n"
        + "assert.ok(long.endsWith('\\u2026'));\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        result = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        Path(path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr
