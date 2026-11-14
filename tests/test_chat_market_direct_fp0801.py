"""FP080.1: a pure price ask is answered straight from the stored Market
Watch data with no AI call at all, so the reply can never fall back to
a "no live access" refusal."""

import time
from unittest.mock import Mock, patch

import main

PIN = "test-pin-1234"
SECRET = "s" * 32

MARKET_DATA = {
    "Gold": 2650.0,
    "Bitcoin": 64200.0,
    "GBP_USD": 1.3352,
}


def _set_market(monkeypatch, data=None, age_seconds=600):
    monkeypatch.setitem(main._finance_cache, "data", dict(data) if data is not None else {})
    monkeypatch.setitem(main._finance_cache, "last_updated", time.time() - age_seconds if data else 0)


def _authed_client(monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_PIN", PIN)
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", SECRET)
    client = main.app.test_client()
    with client.session_transaction() as sess:
        sess["reading_authenticated"] = True
    return client


# --- finance_direct_answer ---

def test_pure_price_ask_gets_direct_answer(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    answer, keys = main.finance_direct_answer("Give me the live gold price")
    assert keys == ["Gold"]
    assert "Gold (per troy ounce): $2,650.00" in answer
    assert "10 minutes ago" in answer


def test_empty_store_direct_answer_points_at_refresh(monkeypatch):
    _set_market(monkeypatch, None)
    answer, keys = main.finance_direct_answer("Gold price right now")
    assert keys == ["Gold"]
    assert "Refresh markets" in answer
    assert "$" not in answer


def test_advice_question_goes_to_model(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    answer, keys = main.finance_direct_answer("gold price and should I buy")
    assert answer is None
    assert keys == []


def test_non_price_question_gets_no_direct_answer(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    answer, keys = main.finance_direct_answer("Tell me about gold mining in Wales")
    assert answer is None
    assert keys == []


def test_long_price_question_goes_to_model(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    answer, keys = main.finance_direct_answer("Can you tell me what the current live gold price is right now please")
    assert answer is None
    assert keys == []


def test_direction_question_goes_to_model(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    answer, keys = main.finance_direct_answer("is gold up today?")
    assert answer is None
    assert keys == []


def test_stale_data_suggests_refresh(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA, age_seconds=2 * 3600)
    answer, keys = main.finance_direct_answer("Gold price?")
    assert "Gold (per troy ounce): $2,650.00" in answer
    assert "2 hours ago" in answer
    assert "newer price" in answer


def test_how_much_question_gets_direct_answer(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    answer, keys = main.finance_direct_answer("How much is gold?")
    assert keys == ["Gold"]
    assert "$2,650.00" in answer


# --- route wiring ---

def test_route_pure_price_ask_skips_provider(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    post = Mock()
    with patch.object(main.requests, "post", post):
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Gold price right now"}]})
    assert response.status_code == 200
    assert "Gold (per troy ounce): $2,650.00" in response.json["reply"]
    assert response.json["provider"] == "Market Watch"
    post.assert_not_called()


def test_route_direct_answer_keeps_web_sources(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    brave = Mock()
    brave.status_code = 200
    brave.json.return_value = {"web": {"results": [{"title": "Kitco gold", "url": "https://example.com/gold", "description": "Live chart."}]}}
    post = Mock()
    with (
        patch.object(main.requests, "get", return_value=brave),
        patch.object(main.requests, "post", post),
    ):
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Gold price right now"}], "web": True})
    assert response.status_code == 200
    assert "Gold (per troy ounce): $2,650.00" in response.json["reply"]
    assert response.json["web_used"] is True
    assert response.json["sources"] == [{"title": "Kitco gold", "url": "https://example.com/gold"}]
    post.assert_not_called()


def test_route_broader_question_still_uses_provider(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    provider = Mock()
    provider.status_code = 200
    provider.json.return_value = {"choices": [{"message": {"content": "It depends."}}]}
    with patch.object(main.requests, "post", return_value=provider) as post:
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Gold price right now — should I buy some?"}]})
    assert response.status_code == 200
    assert response.json["reply"] == "It depends."
    assert response.json["provider"] == "OpenRouter"
    post.assert_called_once()
    system_prompt = post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "Gold (per troy ounce): $2,650.00" in system_prompt


def test_route_empty_store_direct_reply(monkeypatch):
    _set_market(monkeypatch, None)
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    post = Mock()
    with patch.object(main.requests, "post", post):
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Gold price right now"}]})
    assert response.status_code == 200
    assert "Refresh markets" in response.json["reply"]
    post.assert_not_called()
