"""FP122: chat replies read aloud.

Each assistant reply gets a 🔊 Listen button that reads it
with the browser's built-in speech synthesis (free, no key,
en-GB). One reply at a time; tapping again, or another
reply's button, stops it. Leaving the chat stops it too.
Markdown is stripped before speaking so links and formatting
are not read out letter by letter.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def _template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_listen_button_markup():
    html = _template_text()
    assert "chat-speak-btn" in html
    assert "onclick=\"speakChatMessage(${index}, this)\"" in html
    assert ".chat-speak-btn { background:none; border:none; color:var(--faint); font-size:var(--text-base); padding:4px 0 0 12px; cursor:pointer; }" in html
    assert "function chatSpeechSupported()" in html
    assert "function speakableText(markdown) {" in html
    assert "function speakChatMessage(index, button) {" in html
    assert "function stopChatSpeech() {" in html
    # Buttons hide themselves where speech is unsupported.
    start = html.index("function renderChatLog() {")
    window = html[start:start + 800]
    assert "chatSpeechSupported()" in window
    assert ".chat-speak-btn" in window


def test_speech_stops_when_leaving_chat():
    html = _template_text()
    start = html.index("function cacheNewsContainer() {")
    window = html[start:start + 600]
    assert "stopChatSpeech();" in window
    # It goes after the early return, like the other stop calls —
    # the FP099 test pins the exact stopVoiceInput sequence.
    assert window.index("if (newsViewReplaced) return;") < window.index("stopChatSpeech();")
    start = html.index("function restoreNewsContainer() {")
    window = html[start:start + 400]
    assert "stopChatSpeech();" in window


def test_speakable_text_node():
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    html = _template_text()
    match = re.search(r"function speakableText\(markdown\) \{(.*?)\n\}", html, re.S)
    assert match is not None
    script = (
        "import assert from 'node:assert/strict';\n"
        + match.group(0)
        + "\nassert.strictEqual(speakableText('Hello **world**'), 'Hello world');\n"
        + "assert.strictEqual(speakableText('See [the BBC](https://www.bbc.co.uk) for more'), 'See the BBC for more');\n"
        + "assert.strictEqual(speakableText('Run `npm test` now'), 'Run now');\n"
        + "assert.strictEqual(speakableText('## Heading\\nSome *italic* text'), 'Heading Some italic text');\n"
        + "assert.strictEqual(speakableText('Visit https://example.com today'), 'Visit today');\n"
        + "assert.strictEqual(speakableText(''), '');\n"
        + "assert.strictEqual(speakableText(null), '');\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        result = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        Path(path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr


def test_speak_and_stop_node():
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    html = _template_text()
    supported = re.search(r"function chatSpeechSupported\(\) \{(.*?)\n\}", html, re.S)
    speakable = re.search(r"function speakableText\(markdown\) \{(.*?)\n\}", html, re.S)
    speak = re.search(r"function speakChatMessage\(index, button\) \{(.*?)\n\}", html, re.S)
    stop = re.search(r"function stopChatSpeech\(\) \{(.*?)\n\}", html, re.S)
    history = re.search(r"function loadChatHistory\(\) \{(.*?)\n\}", html, re.S)
    key = re.search(r"const CHAT_HISTORY_KEY = '[^']+';", html)
    assert supported is not None
    assert speakable is not None
    assert speak is not None
    assert stop is not None
    assert history is not None
    assert key is not None
    script = (
        "import assert from 'node:assert/strict';\n"
        "const spoken = [];\n"
        "let cancels = 0;\n"
        "class FakeUtterance { constructor(text) { this.text = text; this.lang = ''; } }\n"
        "globalThis.window = { speechSynthesis: { speak(u) { spoken.push(u); }, cancel() { cancels++; } }, SpeechSynthesisUtterance: FakeUtterance };\n"
        "globalThis.SpeechSynthesisUtterance = FakeUtterance;\n"
        "const store = {};\n"
        "globalThis.localStorage = { getItem(k) { return store[k] || null; }, setItem(k, v) { store[k] = v; } };\n"
        "function showChatWebNote(text) {}\n"
        + key.group(0)
        + "\nlet chatSpeechButton = null;\n"
        + supported.group(0)
        + "\n"
        + speakable.group(0)
        + "\n"
        + speak.group(0)
        + "\n"
        + stop.group(0)
        + "\n"
        + history.group(0)
        + "\nstore[CHAT_HISTORY_KEY] = JSON.stringify([{role: 'assistant', content: 'Gold is **$2,650** today.'}, {role: 'assistant', content: 'Second reply.'}]);\n"
        + "const buttonA = {textContent: '🔊 Listen'};\n"
        + "const buttonB = {textContent: '🔊 Listen'};\n"
        + "speakChatMessage(0, buttonA);\n"
        + "assert.strictEqual(spoken.length, 1);\n"
        + "assert.strictEqual(spoken[0].text, 'Gold is $2,650 today.');\n"
        + "assert.strictEqual(spoken[0].lang, 'en-GB');\n"
        + "assert.strictEqual(buttonA.textContent, '⏹ Stop');\n"
        + "speakChatMessage(0, buttonA);\n"
        + "assert.strictEqual(cancels, 2);\n"
        + "assert.strictEqual(buttonA.textContent, '🔊 Listen');\n"
        + "speakChatMessage(0, buttonA);\n"
        + "speakChatMessage(1, buttonB);\n"
        + "assert.strictEqual(spoken.length, 3);\n"
        + "assert.strictEqual(spoken[2].text, 'Second reply.');\n"
        + "assert.strictEqual(buttonA.textContent, '🔊 Listen');\n"
        + "assert.strictEqual(buttonB.textContent, '⏹ Stop');\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        result = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        Path(path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr
