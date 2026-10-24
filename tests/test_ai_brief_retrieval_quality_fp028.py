"""FP028: API integration tests for quality diagnostics and fallback."""
from unittest.mock import patch

import json

import main


def test_live_api_exposes_only_safe_quality_diagnostics(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    article = {"title": "Road funding", "description": "Short teaser", "link": "https://example.com/story"}
    with patch.object(main, "extract_article_text", return_value={
        "success": True,
        "status": "full_text",
        "text": "Detailed transport story. " * 30,
        "quality_score": 82,
        "content_source": "semantic_container",
        "final_url": "https://private.example/secret-path",
    }):
        response = main.app.test_client().post("/api/ai_brief", json={"article": article})
    assert response.status_code == 200
    diagnostics = response.get_json()["retrieval"]
    assert diagnostics["quality_score"] == 82
    assert diagnostics["content_source"] == "semantic_container"
    assert "secret-path" not in response.get_data(as_text=True)
    # With no AI provider configured, the fallback brief may use the article text.
    # The diagnostic metadata itself must not echo article contents.
    assert "Detailed transport story" not in json.dumps(diagnostics)
    assert response.get_json()["brief"]


def test_failed_retrieval_has_neutral_quality_diagnostics_and_keeps_fallback(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with patch.object(main, "extract_article_text", return_value={"success": False, "status": "extraction_failed"}):
        response = main.app.test_client().post("/api/ai_brief", json={"article": {
            "title": "Road funding", "description": "Short feed teaser", "link": "https://example.com/story"
        }})
    assert response.status_code == 200
    diagnostics = response.get_json()["retrieval"]
    assert diagnostics["fallback_used"] is True
    assert diagnostics["quality_score"] == 0
    assert diagnostics["content_source"] == "none"
    assert "Short feed teaser" in response.get_json()["brief"]
