"""FP027 safe diagnostics for automatic article retrieval."""
from unittest.mock import patch

import main


def test_success_reports_safe_full_text_diagnostics(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    article = {"title": "Road repair", "description": "Short teaser", "link": "https://example.com/story", "source": "Example"}
    with patch.object(main, "extract_article_text", return_value={
        "success": True, "status": "full_text", "text": "A detailed article body " * 30,
        "final_url": "https://example.com/story",
    }):
        response = main.app.test_client().post("/api/ai_brief", json={"article": article})
    assert response.status_code == 200
    diagnostics = response.get_json()["retrieval"]
    assert diagnostics["status"] == "full_text"
    assert diagnostics["attempted"] is True
    assert diagnostics["character_count"] > 400
    assert diagnostics["duration_ms"] >= 0
    assert diagnostics["fallback_used"] is False
    assert "retrieved_url" not in diagnostics
    assert "text" not in diagnostics


def test_failed_retrieval_reports_fallback_without_exposing_message(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    article = {"title": "Road repair", "description": "Short teaser", "link": "https://example.com/story"}
    with patch.object(main, "extract_article_text", return_value={
        "success": False, "status": "http_error", "message": "Private transport detail",
    }):
        response = main.app.test_client().post("/api/ai_brief", json={"article": article})
    diagnostics = response.get_json()["retrieval"]
    assert diagnostics["status"] == "http_error"
    assert diagnostics["attempted"] is True
    assert diagnostics["character_count"] == 0
    assert diagnostics["fallback_used"] is True
    assert "Private transport detail" not in response.get_data(as_text=True)
    assert "Short teaser" in response.get_json()["brief"]


def test_pasted_text_reports_skipped_without_fetching(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    article = {"title": "Pasted", "description": "User supplied paragraph", "source_type": "pasted_text", "link": "https://example.com/story"}
    with patch.object(main, "extract_article_text") as extractor:
        response = main.app.test_client().post("/api/ai_brief", json={"article": article})
    extractor.assert_not_called()
    diagnostics = response.get_json()["retrieval"]
    assert diagnostics["status"] == "skipped_pasted_text"
    assert diagnostics["attempted"] is False
    assert diagnostics["fallback_used"] is False


def test_long_description_and_missing_url_report_skip_reason(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = main.app.test_client()
    long_response = client.post("/api/ai_brief", json={"article": {"title": "Long", "description": "x" * 1200, "link": "https://example.com/story"}})
    assert long_response.get_json()["retrieval"]["status"] == "skipped_description_long"
    no_url_response = client.post("/api/ai_brief", json={"article": {"title": "No URL", "description": "Short teaser"}})
    assert no_url_response.get_json()["retrieval"]["status"] == "skipped_no_url"


def test_extractor_exception_is_reported_and_brief_still_returns(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    article = {"title": "Road repair", "description": "Short teaser", "link": "https://example.com/story"}
    with patch.object(main, "extract_article_text", side_effect=RuntimeError("internal detail")):
        response = main.app.test_client().post("/api/ai_brief", json={"article": article})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["retrieval"]["status"] == "extraction_error"
    assert payload["retrieval"]["fallback_used"] is True
    assert "internal detail" not in response.get_data(as_text=True)
