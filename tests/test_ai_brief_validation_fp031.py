"""FP031 regression tests for AI provider and deterministic fallback hardening."""
from unittest.mock import Mock, patch

import main


def valid_brief():
    return (
        "WHAT IS REPORTED\\nExample News reports that a research project was announced. "
        "The available report does not provide further operational details.\\n\\n"
        "WHY IT MATTERS\\nAnalysis: the announcement may indicate future activity, "
        "but its practical significance cannot yet be assessed from the supplied details.\\n\\n"
        "WHAT TO WATCH NEXT\\nLook for official project details, independent reporting, "
        "and updates that clarify scope, funding, and expected milestones."
    )


def article():
    return {
        "title": "Research project announced",
        "description": "Example News reports that a research project was announced.",
        "source": "Example News",
        "source_count": 2,
        "confidence_label": "High",
        "evidence_status": "corroborated",
    }


def provider_response(content, status_code=200):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    return response


def no_provider_keys(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_valid_provider_brief_is_returned_with_validation(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with patch.object(main.requests, "post", return_value=provider_response(valid_brief())):
        response = main.app.test_client().post("/api/ai_brief", json={"article": article()})

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["provider"] == "openrouter"
    assert payload["brief_validation"]["valid"] is True
    assert payload["brief_validation"]["issues"] == []


def test_malformed_provider_response_is_diagnosed_and_valid_fallback_used(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    malformed = Mock()
    malformed.status_code = 200
    malformed.json.return_value = {"unexpected": []}
    with patch.object(main.requests, "post", return_value=malformed), patch.object(
        main, "build_ai_brief_fallback", return_value=valid_brief()
    ):
        response = main.app.test_client().post("/api/ai_brief", json={"article": article()})

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["fallback"] is True
    assert payload["brief_validation"]["valid"] is True
    assert payload["validation_diagnostics"]["rejected_providers"] == [
        {"provider": "openrouter", "reason": "malformed_provider_response"}
    ]


def test_invalid_provider_brief_is_rejected_and_next_provider_is_tried(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "router-test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    with patch.object(
        main.requests,
        "post",
        side_effect=[
            provider_response("This is an invalid short answer."),
            provider_response(valid_brief()),
        ],
    ) as post:
        response = main.app.test_client().post("/api/ai_brief", json={"article": article()})

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["provider"] == "openai"
    assert payload["brief_validation"]["valid"] is True
    rejected = payload["validation_diagnostics"]["rejected_providers"]
    assert len(rejected) == 1
    assert rejected[0]["provider"] == "openrouter"
    assert rejected[0]["reason"] == "brief_validation_failed"
    assert "missing_sections" in rejected[0]["issues"]
    assert "brief_too_short" in rejected[0]["issues"]
    assert payload["validation_diagnostics"]["rejected_provider_count"] == 1
    assert post.call_count == 2


def test_provider_request_exception_is_reported_without_exception_details(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with patch.object(
        main.requests, "post", side_effect=RuntimeError("secret internal detail")
    ), patch.object(main, "build_ai_brief_fallback", return_value=valid_brief()):
        response = main.app.test_client().post("/api/ai_brief", json={"article": article()})

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["validation_diagnostics"]["rejected_providers"] == [
        {"provider": "openrouter", "reason": "provider_request_failed"}
    ]
    assert "secret internal detail" not in response.get_data(as_text=True)


def test_invalid_deterministic_fallback_fails_closed_without_returning_brief(monkeypatch):
    no_provider_keys(monkeypatch)
    with patch.object(
        main, "build_ai_brief_fallback", return_value="Invalid short fallback."
    ):
        response = main.app.test_client().post("/api/ai_brief", json={"article": article()})

    payload = response.get_json()
    assert response.status_code == 502
    assert payload["success"] is False
    assert payload["fallback"] is True
    assert payload["brief_validation"]["valid"] is False
    assert "brief" not in payload
    assert payload["error"] == (
        "Unable to produce a brief that passed structural validation."
    )


def test_fallback_builder_exception_returns_safe_failure(monkeypatch):
    no_provider_keys(monkeypatch)
    with patch.object(
        main, "build_ai_brief_fallback", side_effect=RuntimeError("private detail")
    ):
        response = main.app.test_client().post("/api/ai_brief", json={"article": article()})

    payload = response.get_json()
    assert response.status_code == 502
    assert payload["success"] is False
    assert payload["error"] == "Unable to generate a news brief."
    assert "brief" not in payload
    assert "private detail" not in response.get_data(as_text=True)


def test_provider_http_error_uses_safe_diagnostic(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response_mock = provider_response(valid_brief(), status_code=503)
    with patch.object(main.requests, "post", return_value=response_mock), patch.object(
        main, "build_ai_brief_fallback", return_value=valid_brief()
    ):
        response = main.app.test_client().post("/api/ai_brief", json={"article": article()})

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["validation_diagnostics"]["rejected_providers"] == [
        {"provider": "openrouter", "reason": "provider_http_error"}
    ]
