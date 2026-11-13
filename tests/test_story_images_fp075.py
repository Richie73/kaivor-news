"""FP075: story pictures — publisher images on news cards."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import news_freshness
from news_freshness import entry_image_url
from news_store import normalise_article

import main


# --- RSS extraction ---

def test_media_content_largest_image_wins():
    entry = {"media_content": [
        {"url": "https://example.com/small.jpg", "medium": "image", "width": "120"},
        {"url": "https://example.com/big.jpg", "medium": "image", "width": "1200"},
        {"url": "https://example.com/clip.mp4", "medium": "video"},
    ]}
    assert entry_image_url(entry) == "https://example.com/big.jpg"


def test_media_thumbnail_fallback():
    entry = {"media_thumbnail": [{"url": "https://example.com/thumb.jpg", "width": "150"}]}
    assert entry_image_url(entry) == "https://example.com/thumb.jpg"


def test_enclosure_fallback():
    entry = {"enclosures": [
        {"href": "https://example.com/audio.mp3", "type": "audio/mpeg"},
        {"href": "https://example.com/photo.jpg", "type": "image/jpeg"},
    ]}
    assert entry_image_url(entry) == "https://example.com/photo.jpg"


def test_summary_img_fallback():
    entry = {"summary": '<p>Text <img src="https://example.com/inline.jpg" alt=""></p>'}
    assert entry_image_url(entry) == "https://example.com/inline.jpg"


def test_no_image_returns_empty():
    assert entry_image_url({"title": "No image here"}) == ""
    assert entry_image_url({}) == ""


def test_unsafe_image_urls_rejected():
    entry = {"media_content": [{"url": "javascript:alert(1)", "medium": "image"}]}
    assert entry_image_url(entry) == ""
    entry = {"media_thumbnail": [{"url": "data:image/png;base64,AAAA"}]}
    assert entry_image_url(entry) == ""
    entry = {"media_thumbnail": [{"url": "/relative/path.jpg"}]}
    assert entry_image_url(entry) == ""
    # An unsafe first candidate does not block a valid later one.
    entry = {"media_content": [
        {"url": "javascript:alert(1)", "medium": "image"},
        {"url": "https://example.com/ok.jpg", "medium": "image"},
    ]}
    assert entry_image_url(entry) == "https://example.com/ok.jpg"


def test_rss_items_carry_image_url(monkeypatch):
    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)

    class FakeParsed:
        bozo = False
        feed = {"title": "Test Feed"}
        entries = [
            {
                "title": "With image",
                "link": "https://example.com/one",
                "published": "2026-10-05T11:00:00Z",
                "media_thumbnail": [{"url": "https://example.com/one.jpg"}],
            },
            {
                "title": "Without image",
                "link": "https://example.com/two",
                "published": "2026-10-05T10:00:00Z",
            },
        ]

    response = Mock()
    response.status_code = 200
    response.content = b"<rss></rss>"
    monkeypatch.setattr(news_freshness.requests, "get", lambda *args, **kwargs: response)
    monkeypatch.setattr(news_freshness.feedparser, "parse", lambda *args, **kwargs: FakeParsed())
    feed = {"name": "Test Feed", "url": "https://example.com/rss", "tier": "test"}
    result = news_freshness._fetch_feed(feed, "World", now, 72, 15)
    by_title = {item["title"]: item for item in result}
    assert by_title["With image"]["image_url"] == "https://example.com/one.jpg"
    assert by_title["Without image"]["image_url"] == ""


# --- normalise_article ---

def test_normalise_keeps_image_url():
    item = normalise_article({"title": "T", "link": "https://example.com/x", "image_url": "https://example.com/pic.jpg"})
    assert item["image_url"] == "https://example.com/pic.jpg"


def test_normalise_drops_unsafe_image_url():
    item = normalise_article({"title": "T", "link": "https://example.com/x", "image_url": "javascript:alert(1)"})
    assert item["image_url"] == ""


def test_normalise_defaults_missing_image_url():
    item = normalise_article({"title": "T", "link": "https://example.com/x"})
    assert item["image_url"] == ""


# --- Guardian ---

def test_guardian_requests_and_maps_thumbnail():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"response": {"results": [
        {
            "webTitle": "Guardian story",
            "webUrl": "https://example.com/guardian",
            "webPublicationDate": "2026-11-13T10:00:00Z",
            "fields": {"trailText": "Trail", "thumbnail": "https://example.com/guardian.jpg"},
        }
    ]}}
    with patch.dict(main.os.environ, {"GUARDIAN_API_KEY": "test-key"}):
        with patch.object(main.requests, "get", return_value=response) as get:
            articles = main.fetch_guardian_articles("World")
    assert len(articles) == 1
    assert articles[0]["image_url"] == "https://example.com/guardian.jpg"
    requested_url = get.call_args.args[0]
    assert "show-fields=trailText,thumbnail" in requested_url


# --- NewsData ---

def test_newsdata_maps_image_url():
    payload = {"results": [
        {
            "title": "NewsData story",
            "description": "A full news report body with enough words to pass quality checks.",
            "link": "https://example.com/nd",
            "category": ["world"],
            "source_name": "Example News",
            "pubDate": "2026-11-13 10:00:00",
            "image_url": "https://example.com/nd.jpg",
        }
    ]}
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    with patch.object(main.provider_secrets, "get_provider_key", return_value="test-key"):
        with patch.object(main.requests, "get", return_value=response):
            articles = main.fetch_newsdata_articles()
    assert len(articles) == 1
    assert articles[0]["image_url"] == "https://example.com/nd.jpg"


# --- template ---

def _template_text():
    return (Path(__file__).resolve().parent.parent / "templates" / "index.html").read_text(encoding="utf-8")


def test_template_renders_card_images():
    text = _template_text()
    assert ".card-image" in text
    assert 'class="card-image"' in text
    assert 'loading="lazy"' in text
    assert 'referrerpolicy="no-referrer"' in text
    assert "onerror=\"this.style.display='none'\"" in text
    # Server-rendered card and saved-stories card both render the image.
    assert "{% if article.image_url %}" in text
    assert "${article.image_url ?" in text
    # Saving a story keeps its picture.
    assert "image_url: card.querySelector('.card-image')?.src || ''" in text
