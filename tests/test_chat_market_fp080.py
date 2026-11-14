"""FP080: Market Watch prices in the chat hub. Price questions about a
tracked asset get the app's own stored market values in the system
prompt, whether web search is on or off."""

import time
from unittest.mock import Mock, patch

import main

PIN = "test-pin-1234"
SECRET = "s" * 32

MARKET_DATA = {
    "Gold": 2650.0,
    "Bitcoin": 64200.0,
    "SP500": 5750.0,
    "Brent_Oil": 75.0,
    "GBP_USD": 1.3352,
    "GBP_EUR": 1.19,
    "EUR_USD": 1.08,
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


def _provider_response(text):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"choices": [{"message": {"content": text}}]}
    return response


# --- finance_context_for_chat ---

def test_gold_price_question_gets_value(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    block, keys = main.finance_context_for_chat("Gold price right now")
    assert keys == ["Gold"]
    assert "Gold (per troy ounce): $2,650.00" in block
    assert "fetched" in block
    assert "10 minutes ago" in block
    assert "Do not invent a newer price." in block


def test_short_asset_question_matches(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    block, keys = main.finance_context_for_chat("What's bitcoin at?")
    assert keys == ["Bitcoin"]
    assert "Bitcoin: $64,200.00" in block


def test_non_price_question_gets_nothing(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    block, keys = main.finance_context_for_chat("Tell me about gold mining in Wales")
    assert block == ""
    assert keys == []


def test_fx_pair_question(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    block, keys = main.finance_context_for_chat("What's the pound to dollar rate?")
    assert keys == ["GBP_USD"]
    assert "GBP/USD: 1.3352" in block


def test_empty_store_points_at_refresh_markets(monkeypatch):
    _set_market(monkeypatch, None)
    block, keys = main.finance_context_for_chat("Gold price?")
    assert keys == ["Gold"]
    assert "$" not in block
    assert "Refresh markets" in block
    assert "Do not guess a price." in block


def test_multiple_assets(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    block, keys = main.finance_context_for_chat("gold and bitcoin prices")
    assert keys == ["Gold", "Bitcoin"]
    assert "Gold (per troy ounce): $2,650.00" in block
    assert "Bitcoin: $64,200.00" in block


def test_oil_price_matches_brent(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    block, keys = main.finance_context_for_chat("oil price today")
    assert keys == ["Brent_Oil"]
    assert "Brent crude oil (per barrel): $75.00" in block


# --- route wiring ---

def _chat_with_capture(monkeypatch, message, web=False, brave_results=None):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["payload"] = json
        return _provider_response("ok")

    patches = [patch.object(main.requests, "post", side_effect=fake_post)]
    if web:
        monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
        brave = Mock()
        brave.status_code = 200
        brave.json.return_value = {"web": {"results": brave_results or []}}
        patches.append(patch.object(main.requests, "get", return_value=brave))
    with patches[0], (patches[1] if len(patches) > 1 else _nullcontext()):
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": message}], "web": web})
    return response, captured


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


def test_route_injects_market_data_without_web(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    response, captured = _chat_with_capture(monkeypatch, "Gold price right now")
    assert response.status_code == 200
    system_prompt = captured["payload"]["messages"][0]["content"]
    assert "Gold (per troy ounce): $2,650.00" in system_prompt
    assert response.json["web_used"] is False


def test_route_combines_market_data_and_web(monkeypatch):
    _set_market(monkeypatch, MARKET_DATA)
    response, captured = _chat_with_capture(
        monkeypatch,
        "Gold price right now",
        web=True,
        brave_results=[{"title": "Kitco gold", "url": "https://example.com/gold", "description": "Live chart."}],
    )
    assert response.status_code == 200
    system_prompt = captured["payload"]["messages"][0]["content"]
    assert "Gold (per troy ounce): $2,650.00" in system_prompt
    assert "[1] Kitco gold" in system_prompt
    assert response.json["web_used"] is True


def test_route_empty_store_prompts_refresh(monkeypatch):
    _set_market(monkeypatch, None)
    response, captured = _chat_with_capture(monkeypatch, "Gold price right now")
    assert response.status_code == 200
    assert "Refresh markets" in captured["payload"]["messages"][0]["content"]


def test_route_logs_finance_keys(monkeypatch, capsys):
    _set_market(monkeypatch, MARKET_DATA)
    response, _ = _chat_with_capture(monkeypatch, "Gold price right now")
    assert response.status_code == 200
    assert "finance=Gold" in capsys.readouterr().out
