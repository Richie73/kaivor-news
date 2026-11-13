"""FP069 tests for snapshot/gitignore exclusions of key-bearing paths.

A live-format OpenRouter key once shipped in stale local_config.py copies
because neither the snapshot exclusions nor .gitignore covered those paths.
These tests pin the exclusions and the snapshot script's content scan, and
assert no live-format key remains anywhere in the tree outside the device's
sanctioned secret store (config/news_secrets.json, config/secrets.py,
.env — the paths the snapshot script excludes by name). The token-shaped
fake fixture in tests/test_kaimprove_fp035.py contains underscores, so it
does not match the 20+ consecutive-alphanumeric pattern and must not trip
the scan.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_PATHS = ["config/local_config.py", "releases/", "Kaivor/", "kaivor_fp0172/"]

# The device's sanctioned secret store legitimately holds the live key.
# These paths are excluded from snapshots by name (see kaivor_snapshot.sh).
SANCTIONED_SECRET_PATHS = {
    "config/news_secrets.json",
    "config/secrets.py",
    ".env",
}

BINARY_SUFFIXES = {
    ".zip", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".woff", ".woff2",
    ".ttf", ".db", ".sqlite", ".sqlite3", ".pyc", ".pdf", ".mp3", ".mp4",
}


def test_gitignore_excludes_key_bearing_paths():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in EXCLUDED_PATHS:
        assert entry in text


def test_snapshot_script_excludes_key_bearing_paths():
    text = (ROOT / "scripts" / "kaivor_snapshot.sh").read_text(encoding="utf-8")
    for entry in ["config/local_config.py", "releases", "Kaivor", "kaivor_fp0172"]:
        assert entry in text


def test_snapshot_script_scans_contents_for_key_patterns():
    text = (ROOT / "scripts" / "kaivor_snapshot.sh").read_text(encoding="utf-8")
    assert "sk-or-v1-[A-Za-z0-9]{20,}" in text
    assert "sk-proj-[A-Za-z0-9]{20,}" in text
    assert "sk-[A-Za-z0-9]{20,}" in text


def test_no_live_format_openrouter_key_in_tree():
    pattern = re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}")
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or ".git" in path.parts:
            continue
        rel = str(path.relative_to(ROOT))
        if rel in SANCTIONED_SECRET_PATHS:
            continue
        if rel.startswith("config/") and rel.endswith(".json") and "secrets" in rel:
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        if pattern.search(content):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
