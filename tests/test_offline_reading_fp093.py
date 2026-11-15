"""FP093: offline reading — the service worker caches the last
rendered homepage, and the page says when it was rendered.

Before this milestone the worker's navigation fallback
(caches.match('/')) could never hit, because nothing ever put '/'
in the cache — offline, the app showed the browser's error page.
Now a successful navigation is stored under its own URL, and an
offline open serves the exact page asked for (or the homepage).
The page carries the news cache's last-updated time on the
offline banner, so the reader knows how old the stories are.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from unittest.mock import patch

import pytest

import main

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "index.html"
WORKER = ROOT / "static" / "service-worker.js"

NODE_ASSERTIONS = """
assert.equal(formatOfflineTime(0), '');
assert.equal(formatOfflineTime(null), '');
assert.equal(formatOfflineTime(undefined), '');
assert.match(formatOfflineTime(1794546000), /^\\d{2}:\\d{2}$/);
"""


def test_worker_caches_successful_navigations():
    js = WORKER.read_text(encoding="utf-8")
    assert "const CACHE = 'kaivor-news-fp093-offline-v1';" in js
    assert "if (response.ok) {" in js
    assert "response.clone()" in js
    assert "cache.put(request, copy)" in js


def test_worker_offline_fallback_serves_cached_page_then_home():
    js = WORKER.read_text(encoding="utf-8")
    assert "caches.match(request).then(cached => cached || caches.match('/'))" in js


def test_worker_still_passes_through_api_and_cross_origin():
    js = WORKER.read_text(encoding="utf-8")
    assert "if (request.method !== 'GET') return;" in js
    assert "if (url.origin !== self.location.origin) return;" in js
    assert "if (url.pathname.startsWith('/api/')) return;" in js


def test_offline_banner_markup_present():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="offline-banner"' in html
    assert 'data-news-updated="{{ news_last_updated|int }}"' in html
    assert 'id="offline-banner-text"' in html
    assert "#offline-banner {" in html


def test_banner_updates_on_connectivity_changes():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "function updateOfflineBanner() {" in html
    assert "window.addEventListener('online', updateOfflineBanner);" in html
    assert "window.addEventListener('offline', updateOfflineBanner);" in html
    assert "You're offline — showing stories from" in html
    assert "You're offline — showing your last loaded stories." in html


def test_banner_checked_on_page_load():
    html = TEMPLATE.read_text(encoding="utf-8")
    match = re.search(
        r"document\.addEventListener\('DOMContentLoaded',\(\)=>\{(.*?)\}\);",
        html,
        re.S,
    )
    assert match, "main DOMContentLoaded handler missing"
    assert "updateOfflineBanner();" in match.group(1)


def test_index_passes_news_last_updated_to_template():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'news_last_updated = float(_news_cache.get("last_updated") or 0)' in source
    assert "news_last_updated=news_last_updated" in source


def test_home_page_stamps_last_updated_on_banner():
    article = {
        "id": "fp093-home-1",
        "title": "Offline banner test",
        "source": "Example Publisher",
        "category": "World",
        "cluster_id": "cluster-1",
        "source_count": 1,
        "report_count": 1,
        "repeated_same_source_reports": 0,
        "story_sources": [],
        "importance_score": 50,
        "importance_label": "Medium",
        "confidence_score": 50,
        "confidence_label": "Low",
        "relevance_score": 50,
        "relevance_label": "Medium",
        "sport_focus": "other",
        "published_ts": 0,
        "published": "Recent",
        "link": "https://example.com/story",
        "feed_tier": "supplemental",
        "feed_url": "https://newsdata.io/api/1/latest",
        "evidence_status": "Single-source",
    }

    with patch.object(main, "_ensure_news_refresh_started"):
        with patch.object(
            main, "_news_cache", {"articles": [article], "last_updated": 1794546000}
        ):
            with patch.object(main, "_finance_cache", {"data": {}}):
                with patch.object(main, "load_saved_articles", return_value=[]):
                    response = main.app.test_client().get("/")

    assert response.status_code == 200
    assert b'data-news-updated="1794546000"' in response.data


def test_offline_time_format_runs_under_node():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    html = TEMPLATE.read_text(encoding="utf-8")
    match = re.search(
        r"function formatOfflineTime\(epochSeconds\) \{(.*?)\n\}",
        html,
        re.S,
    )
    assert match, "formatOfflineTime helper missing"
    js = match.group(0)
    script = "import assert from 'node:assert/strict';\n" + js + NODE_ASSERTIONS
    with tempfile.NamedTemporaryFile(
        "w", suffix=".mjs", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(script)
        path = handle.name
    result = subprocess.run(
        [node, path], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
