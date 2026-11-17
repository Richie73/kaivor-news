"""FP116: the app is called Kaivor now, not Kaivor News.

News is one of six things on the bottom bar — chat, memory,
tasks, RAMS and receipts sit next to it — so the old name
undersold it. The header, splash, page title, Settings About
line, PWA manifest and the AI prompts all say Kaivor, with the
tagline "Your personal AI".

Deliberately unchanged: the icon filenames (kaivor-news-*.png),
the web address, the service worker cache name, and module
docstrings (historical FP references, not user-visible).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "templates" / "index.html"
READING = ROOT / "templates" / "reading.html"
MANIFEST = ROOT / "static" / "manifest.webmanifest"

OLD_BRANDING = ("Kaivor News", "KAIVOR NEWS", "Global Intelligence")


def test_home_title_is_kaivor():
    assert "<title>Kaivor</title>" in INDEX.read_text(encoding="utf-8")


def test_header_brand_and_tagline():
    html = INDEX.read_text(encoding="utf-8")
    assert '>KAIVOR</div><div class="sub-header">Your personal AI</div>' in html


def test_splash_word_and_tagline():
    html = INDEX.read_text(encoding="utf-8")
    assert '<div class="splash-word">KAIVOR</div>' in html
    assert '<div class="splash-tag">Your personal AI</div>' in html


def test_settings_about_line_says_kaivor():
    html = INDEX.read_text(encoding="utf-8")
    assert "'<p class=\"evidence-note\">Kaivor'" in html


def test_manifest_name_and_description():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["name"] == "Kaivor"
    assert manifest["short_name"] == "Kaivor"
    assert manifest["description"].startswith("Your personal AI")
    # The Spark K icons are unchanged — only the name moved.
    assert manifest["icons"][0]["src"] == "/icons/kaivor-news-192-v3.png"


def test_reading_brand_is_kaivor():
    html = READING.read_text(encoding="utf-8")
    assert '<div class="brand">KAIVOR</div>' in html
    # The Reading page keeps its own title and sub-heading.
    assert "<title>Kaivor Reading</title>" in html
    assert '<div class="sub">Reading Intelligence</div>' in html


def test_no_old_branding_in_user_facing_files():
    for path in (INDEX, READING, MANIFEST):
        text = path.read_text(encoding="utf-8")
        for old in OLD_BRANDING:
            assert old not in text, f"{old} still in {path.name}"


def test_ai_prompts_say_kaivor():
    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'system="You are Kaivor. Answer the user\'s question about the supplied article' in main_text
    analyst_text = (ROOT / "confidence_aware_ai.py").read_text(encoding="utf-8")
    assert "You are Kaivor's cautious evidence-grounded news analyst." in analyst_text
