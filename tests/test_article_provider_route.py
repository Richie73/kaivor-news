"""Provider attribution API tests."""

from unittest.mock import patch

import main


def test_saved_articles_include_provider_label():
    saved = [
        {
            "id": "newsdata-1",
            "title": "Example story",
            "source": "Example Publisher",
            "feed_tier": "supplemental",
            "feed_url": "https://newsdata.io/api/1/latest",
        }
    ]

    with patch.object(main, "load_saved_articles", return_value=saved):
        response = main.app.test_client().get("/api/saved")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["articles"][0]["provider"] == "NewsData.io"


def test_home_page_renders_provider_badge():
    article = {
        "id": "newsdata-home-1",
        "title": "Provider badge test",
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
        with patch.object(main, "_news_cache", {"articles": [article]}):
            with patch.object(main, "_finance_cache", {"data": {}}):
                with patch.object(main, "load_saved_articles", return_value=[]):
                    response = main.app.test_client().get("/")

    assert response.status_code == 200
    assert b"NewsData.io" in response.data
    assert b"Provider badge test" in response.data
