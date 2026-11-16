"""FP099: voice input in the chat hub.

The chat form gains a microphone button using the browser's
built-in speech recognition (Chrome on Android) — free, no key,
no server round-trip. The transcript lands in the input and the
user taps Send as normal; nothing is ever sent automatically.
The button hides itself where the browser has no speech
recognition, and the mic stops when the user leaves the chat.
"""
import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def function_body(html, name):
    match = re.search(
        rf"function {name}\(.*?\n\}}", html, re.S
    )
    assert match, f"{name} missing"
    return match.group(0)


def test_voice_button_in_chat_form():
    html = template_text()
    assert (
        '<button type="button" id="chat-voice-btn" class="chat-voice-btn" '
        'onclick="toggleVoiceInput(this)" title="Speak instead of typing">🎤</button>'
        in html
    )


def test_voice_uses_browser_speech_recognition():
    html = template_text()
    assert "window.SpeechRecognition || window.webkitSpeechRecognition" in html
    assert "recognition.lang = 'en-GB';" in html
    assert "recognition.interimResults = true;" in html
    assert "recognition.continuous = false;" in html


def test_voice_button_hidden_when_unsupported():
    html = template_text()
    assert "if (!chatVoiceSupported())" in html
    assert "voiceBtn.style.display = 'none';" in html


def test_voice_stops_when_leaving_chat():
    html = template_text()
    assert "stopVoiceInput();\n    if (newsViewReplaced) return;" in html
    assert "stopVoiceInput();\n    if (!newsViewReplaced) return true;" in html


def test_voice_listening_style():
    html = template_text()
    assert ".chat-voice-btn.listening { background:#7f1d1d; border-color:#ef4444; }" in html


def test_voice_does_not_auto_send():
    html = template_text()
    body = function_body(html, "toggleVoiceInput")
    assert "sendChatMessage" not in body
    assert ".submit(" not in body
    assert "target.value = (baseText ? baseText + ' ' : '') + interim;" in body
