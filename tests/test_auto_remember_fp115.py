"""FP115: auto-remembering — after a chat reply, a background
thread asks the provider what (if anything) in the exchange is
worth remembering, skips duplicates, and saves the rest with
source "auto". Opt-in only: the client sends "auto_remember": true
(the chat UI sends its toggle state, on by default). Pure price
asks never trigger it, even when opted in."""

import sqlite3
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import main
from auto_remember import (
    distinctive_words,
    extract_and_save_memories,
    memory_already_saved,
    parse_extracted_memories,
)
from core.memory import api as memory_api
from core.memory import database as memory_db
from core.memory.models import Memory

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

PIN = "test-pin-1234"
SECRET = "test-session-secret-0123456789abcdef"


class _FakeManager:
    def __init__(self, reply=None, error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def generate_with_fallback(self, request, **kwargs):
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return ("OpenRouter", self.reply)


class _FakeThread:
    started = []

    def __init__(self, target=None, daemon=None):
        self.target = target

    def start(self):
        _FakeThread.started.append(self.target)
        self.target()  # run inline, so the route test sees the result


@pytest.fixture
def tmp_memory_db(monkeypatch, tmp_path):
    db_path = tmp_path / "mem.db"
    monkeypatch.setattr(memory_db, "DB_PATH", db_path)
    monkeypatch.setattr(memory_api, "_manager", None)
    monkeypatch.delenv("KAIVOR_READING_DATABASE_URL", raising=False)
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


# --- distinctive_words ---


def test_distinctive_words_skips_short_and_stopwords():
    assert distinctive_words("What does my scaffold ticket cover?") == [
        "scaffold", "ticket", "cover",
    ]


def test_distinctive_words_dedupes_and_caps():
    words = distinctive_words("groundworks groundworks civils drainage piling steel concrete formwork rebar", limit=4)
    assert words == ["groundworks", "civils", "drainage", "piling"]


def test_distinctive_words_unlimited_with_none():
    words = distinctive_words("alpha bravo charlie delta echo foxtrot golf hotel india juliett kilo lima", limit=None)
    assert len(words) == 12


# --- parse_extracted_memories ---


def test_parse_valid_json():
    parsed = parse_extracted_memories(
        '{"memories": [{"title": "Prefers groundworks", '
        '"content": "Richie prefers groundworks jobs near Chester.", "category": "work"}]}'
    )
    assert parsed == [(
        "Prefers groundworks",
        "Richie prefers groundworks jobs near Chester.",
        "work",
    )]


def test_parse_strips_code_fences():
    parsed = parse_extracted_memories(
        '```json\n{"memories": [{"title": "T", "content": "C"}]}\n```'
    )
    assert parsed == [("T", "C", "general")]


def test_parse_rejects_garbage():
    assert parse_extracted_memories("") == []
    assert parse_extracted_memories("not json at all") == []
    assert parse_extracted_memories('{"memories": "nope"}') == []
    assert parse_extracted_memories('{"memories": [{"title": "", "content": "C"}]}') == []
    assert parse_extracted_memories('{"memories": [{"title": "T"}]}') == []
    assert parse_extracted_memories("[]") == []


def test_parse_caps_at_three_and_truncates():
    items = ", ".join(
        '{"title": "%s", "content": "C%d"}' % ("x" * 250, i) for i in range(5)
    )
    parsed = parse_extracted_memories('{"memories": [%s]}' % items)
    assert len(parsed) == 3
    assert len(parsed[0][0]) == 200


# --- memory_already_saved ---


def _memory(title, content):
    return Memory(id=None, category="general", title=title, content=content)


def test_duplicate_by_title():
    existing = [_memory("Prefers groundworks", "Likes civils work.")]
    assert memory_already_saved("prefers GROUNDWORKS", "Something else entirely.", existing) is True


def test_duplicate_by_shared_words():
    existing = [_memory("IPAF ticket", "IPAF 3a and 3b until June 2030.")]
    assert memory_already_saved(
        "Licence dates", "IPAF 3a and 3b expire in June 2030.", existing
    ) is True


def test_not_a_duplicate_when_words_differ():
    existing = [_memory("IPAF ticket", "IPAF 3a and 3b until June 2030.")]
    assert memory_already_saved(
        "Favourite pub lunch", "The Plough in Puddington does a good pie.", existing
    ) is False


# --- extract_and_save_memories ---


def test_skips_short_user_messages():
    manager = _FakeManager(reply='{"memories": []}')
    saved, skipped = extract_and_save_memories(
        "Hi there", "Hello!", manager=manager,
        remember=Mock(), recall=lambda: [],
    )
    assert (saved, skipped) == (0, 0)
    assert manager.calls == []


def test_saves_new_memories_as_auto():
    manager = _FakeManager(reply='{"memories": [{"title": "Prefers groundworks", "content": "Richie prefers groundworks jobs near Chester.", "category": "work"}]}')
    saved_memories = []

    def remember(category, title, content, source="manual"):
        saved_memories.append((category, title, content, source))

    saved, skipped = extract_and_save_memories(
        "I prefer working on groundworks jobs near Chester",
        "Noted — groundworks near Chester it is.",
        manager=manager, remember=remember, recall=lambda: [],
    )
    assert (saved, skipped) == (1, 0)
    assert saved_memories == [(
        "work", "Prefers groundworks",
        "Richie prefers groundworks jobs near Chester.", "auto",
    )]
    assert manager.calls[0].temperature == 0.1


def test_skips_duplicates_and_counts_them():
    manager = _FakeManager(reply='{"memories": [{"title": "Prefers groundworks", "content": "Richie prefers groundworks jobs near Chester."}]}')
    existing = [_memory("Prefers groundworks", "Likes groundworks near Chester.")]
    saved, skipped = extract_and_save_memories(
        "I prefer working on groundworks jobs near Chester",
        "Noted.",
        manager=manager, remember=Mock(), recall=lambda: existing,
    )
    assert (saved, skipped) == (0, 1)


def test_saves_nothing_when_model_finds_nothing():
    manager = _FakeManager(reply='{"memories": []}')
    remember = Mock()
    saved, skipped = extract_and_save_memories(
        "What is the weather like tomorrow in Puddington",
        "Rain, 12 degrees.",
        manager=manager, remember=remember, recall=lambda: [],
    )
    assert (saved, skipped) == (0, 0)
    remember.assert_not_called()


def test_provider_failure_returns_zero():
    manager = _FakeManager(error=RuntimeError("provider down"))
    saved, skipped = extract_and_save_memories(
        "I prefer working on groundworks jobs near Chester",
        "Noted.",
        manager=manager, remember=Mock(), recall=lambda: [],
    )
    assert (saved, skipped) == (0, 0)


def test_dedupes_within_one_batch():
    manager = _FakeManager(reply='{"memories": ['
        '{"title": "Prefers groundworks", "content": "Richie prefers groundworks jobs near Chester."}, '
        '{"title": "Groundworks preference", "content": "Richie prefers groundworks jobs around Chester."}]}')
    remember = Mock()
    saved, skipped = extract_and_save_memories(
        "I prefer working on groundworks jobs near Chester",
        "Noted.",
        manager=manager, remember=remember, recall=lambda: [],
    )
    assert (saved, skipped) == (1, 1)
    assert remember.call_count == 1


# --- chat wiring ---


def test_chat_auto_remembers_in_background(monkeypatch, tmp_memory_db):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    _FakeThread.started.clear()

    def post(url, **kwargs):
        payload = kwargs.get("json") or {}
        messages = payload.get("messages") or []
        system = messages[0].get("content", "") if messages else ""
        if "durable facts" in system:
            return _provider_response(
                '{"memories": [{"title": "Prefers groundworks", '
                '"content": "Richie prefers groundworks jobs near Chester.", "category": "work"}]}'
            )
        return _provider_response("Noted — groundworks near Chester.")

    with (
        patch.object(main.threading, "Thread", _FakeThread),
        patch.object(main.requests, "post", side_effect=post),
    ):
        response = client.post("/api/chat", json={"messages": [
            {"role": "user", "content": "I prefer working on groundworks jobs near Chester"},
        ], "auto_remember": True})
    assert response.status_code == 200
    assert response.json["reply"] == "Noted — groundworks near Chester."
    assert len(_FakeThread.started) == 1
    conn = sqlite3.connect(tmp_memory_db)
    rows = conn.execute("SELECT title, source FROM memories").fetchall()
    conn.close()
    assert rows == [("Prefers groundworks", "auto")]


def test_chat_skips_auto_remember_when_opted_out(monkeypatch, tmp_memory_db):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    _FakeThread.started.clear()
    with (
        patch.object(main.threading, "Thread", _FakeThread),
        patch.object(main.requests, "post", return_value=_provider_response("Hello.")),
    ):
        response = client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "I prefer working on groundworks jobs near Chester"}],
            "auto_remember": False,
        })
    assert response.status_code == 200
    assert _FakeThread.started == []


def test_chat_skips_auto_remember_for_direct_price_answer(monkeypatch, tmp_memory_db):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setitem(main._finance_cache, "data", {"Gold": 3000.0})
    monkeypatch.setitem(main._finance_cache, "last_updated", time.time())
    _FakeThread.started.clear()
    with patch.object(main.threading, "Thread", _FakeThread):
        response = client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Give me the live gold price"}],
            "auto_remember": True,  # opted in, but the direct path still skips it
        })
    assert response.status_code == 200
    assert response.json["provider"] == "Market Watch"
    assert _FakeThread.started == []


# --- template ---


def test_auto_remember_toggle_markup():
    html = _template_text()
    assert "const CHAT_AUTO_REMEMBER_KEY = 'kaivor-auto-remember';" in html
    assert 'id="chat-auto-remember"' in html
    assert "function saveChatAutoRememberToggle() {" in html
    assert "localStorage.getItem(CHAT_AUTO_REMEMBER_KEY) !== '0'" in html
    assert "auto_remember: autoRemember" in html
