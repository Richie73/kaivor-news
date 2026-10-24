"""FP026 integration tests for automatic article retrieval before briefing."""
from unittest.mock import patch

import main


def test_ai_brief_uses_retrieved_text_when_feed_description_is_short(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    article = {
        "title": "Road repair programme",
        "description": "Short feed teaser.",
        "link": "https://example.com/roads",
        "source": "Example News",
        "category": "UK",
        "source_count": 1,
        "report_count": 1,
        "confidence_label": "Low",
        "evidence_status": "Single-source",
    }
    with patch.object(main, "extract_article_text", return_value={
        "success": True,
        "status": "full_text",
        "text": "Full article body " * 40,
        "final_url": "https://example.com/roads",
    }) as extract:
        response = main.app.test_client().post("/api/ai_brief", json={"article": article})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    extract.assert_called_once_with("https://example.com/roads")
    assert "Full article body" in payload["brief"]


def test_ai_brief_keeps_feed_description_when_retrieval_fails(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    article = {
        "title": "Road repair programme",
        "description": "Short feed teaser.",
        "link": "https://example.com/roads",
        "source": "Example News",
    }
    with patch.object(main, "extract_article_text", return_value={
        "success": False,
        "status": "http_error",
        "message": "Publisher returned an error.",
    }):
        response = main.app.test_client().post("/api/ai_brief", json={"article": article})
    assert response.status_code == 200
    assert "Short feed teaser." in response.get_json()["brief"]


def test_pasted_text_never_triggers_automatic_retrieval(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    article = {
        "title": "User supplied",
        "description": "A pasted paragraph.",
        "link": "https://example.com/story",
        "source_type": "pasted_text",
    }
    with patch.object(main, "extract_article_text") as extract:
        response = main.app.test_client().post("/api/ai_brief", json={"article": article})
    assert response.status_code == 200
    extract.assert_not_called()
    assert "pasted paragraph" in response.get_json()["brief"]
