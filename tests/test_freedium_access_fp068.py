"""FP068 tests for Freedium unlock links (publisher_access + main + template)."""
from pathlib import Path

import main
import publisher_access
from publisher_access import freedium_access_info, freedium_url_for

MIRROR_BASE = "https://freedium-mirror.cfd"

FREEDIUM_URLS = [
    "https://medium.com/@author/story-123",
    "https://www.nytimes.com/2026/11/12/world/story.html",
    "https://www.washingtonpost.com/world/story",
    "https://www.bloomberg.com/news/articles/story",
    "https://www.reuters.com/world/story",
    "https://www.economist.com/business/story",
    "https://www.ft.com/content/story",
]


def test_freedium_url_for_all_seven_domains():
    for url in FREEDIUM_URLS:
        assert freedium_url_for(url) == MIRROR_BASE + "/" + url


def test_freedium_url_for_accepts_subdomains():
    assert freedium_url_for("https://www.medium.com/story") == MIRROR_BASE + "/https://www.medium.com/story"
    assert freedium_url_for("https://api.ft.com/content/story") == MIRROR_BASE + "/https://api.ft.com/content/story"


def test_freedium_url_for_rejects_attacker_domains():
    assert freedium_url_for("https://nytimes.com.attacker.example/story") is None
    assert freedium_url_for("https://medium.com.evil.org/story") is None
    assert freedium_url_for("https://fakeft.com/content/story") is None
    assert freedium_url_for("https://notmedium.com/story") is None


def test_freedium_url_for_rejects_non_http_and_invalid():
    assert freedium_url_for("ftp://medium.com/story") is None
    assert freedium_url_for("") is None
    assert freedium_url_for(None) is None
    assert freedium_url_for("not a url") is None


def test_freedium_url_for_rejects_oversized_url():
    assert freedium_url_for("https://medium.com/" + "a" * 2100) is None


def test_freedium_access_info_shapes():
    available = freedium_access_info("https://medium.com/@author/story-123")
    assert available["available"] is True
    assert available["url"] == MIRROR_BASE + "/https://medium.com/@author/story-123"
    assert available["label"] == "Unlock via Freedium"
    unavailable = freedium_access_info("https://example.com/story")
    assert unavailable == {"available": False, "url": "", "label": "Unlock via Freedium"}


def test_publisher_access_info_unchanged():
    # FP068 adds Freedium metadata without changing the subscription behaviour.
    assert publisher_access.publisher_access_info("The New York Times", "https://www.nytimes.com/story") == {
        "supported": True,
        "publisher": "The New York Times",
        "label": "Open with your NYT subscription",
    }
    assert publisher_access.publisher_access_info("Medium", "https://medium.com/story") == {
        "supported": False,
        "publisher": "",
        "label": "Open original article",
    }


def test_main_article_freedium_access():
    assert main.article_freedium_access({"link": "https://www.reuters.com/world/story"})["available"] is True
    assert main.article_freedium_access({"link": "https://example.com/story"})["available"] is False
    assert main.article_freedium_access({})["available"] is False


def test_template_renders_freedium_link():
    template = Path("templates/index.html").read_text(encoding="utf-8")
    assert "article_freedium_access(article).available" in template
    assert "Unlock via Freedium" in template
    assert "article_freedium_access(article).url" in template
