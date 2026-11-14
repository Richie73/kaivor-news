"""FP086: price history for the Markets view (server side).

History comes from the same free sources as the live prices — Yahoo
Finance chart data (range=5d, interval=1d) for the four USD assets,
Frankfurter timeseries for the three FX pairs — so nothing is stored
and no migration is needed. The current price prefers the stored
Market Watch value so the view agrees with the ticker.
"""
from unittest.mock import patch

import main


YAHOO_GOLD = {
    "chart": {"result": [{
        "meta": {
            "regularMarketPrice": 3886.3,
            "chartPreviousClose": 4114.5,
            "regularMarketDayHigh": 3927.2,
            "regularMarketDayLow": 3871.1,
        },
        "timestamp": [1794200400, 1794286800, 1794373200, 1794459600, 1794546000],
        "indicators": {"quote": [{"close": [4114.5, 4030.2, 4000.5, 3885.3, 3886.3]}]},
    }]},
}

FX_GBP = {"rates": {
    "2026-11-09": {"USD": 1.3416, "EUR": 1.1986, "JPY": 210.45},
    "2026-11-10": {"USD": 1.3423, "EUR": 1.197, "JPY": 210.88},
    "2026-11-11": {"USD": 1.3307, "EUR": 1.1959, "JPY": 211.02},
    "2026-11-12": {"USD": 1.3256, "EUR": 1.1962, "JPY": 211.35},
    "2026-11-13": {"USD": 1.3227, "EUR": 1.1968, "JPY": 211.62},
}}

FX_EUR = {"rates": {
    "2026-11-09": {"USD": 1.1194},
    "2026-11-10": {"USD": 1.1211},
    "2026-11-11": {"USD": 1.1129},
    "2026-11-12": {"USD": 1.1082},
    "2026-11-13": {"USD": 1.1042},
}}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def fake_get(url, **kwargs):
    if "yahoo" in url:
        return FakeResponse(YAHOO_GOLD)
    if "from=GBP" in url:
        return FakeResponse(FX_GBP)
    if "from=EUR" in url:
        return FakeResponse(FX_EUR)
    raise AssertionError(f"unexpected url {url}")


def reset_history_cache():
    main._finance_history_cache["data"] = {}
    main._finance_history_cache["last_updated"] = 0


def reset_finance_cache():
    # test_finance_fp0182 leaves {"Gold": 3000.0} in the store; the
    # history tests must not depend on whatever ran before them.
    main._finance_cache["data"] = {}
    main._finance_cache["last_updated"] = 0


def test_yahoo_history_parses_meta_and_series():
    with patch.object(main.requests, "get", side_effect=fake_get):
        entry = main._fetch_yahoo_history("GC=F")
    assert entry["current"] == 3886.3
    assert entry["previous_close"] == 4114.5
    assert entry["day_high"] == 3927.2
    assert entry["day_low"] == 3871.1
    assert len(entry["series"]) == 5
    assert entry["series"][0] == {"date": "2026-11-09", "close": 4114.5}
    assert entry["series"][-1] == {"date": "2026-11-13", "close": 3886.3}


def test_yahoo_history_returns_none_on_failure():
    with patch.object(main.requests, "get", side_effect=Exception("boom")):
        assert main._fetch_yahoo_history("GC=F") is None
    with patch.object(main.requests, "get", return_value=FakeResponse({"chart": {"result": []}})):
        assert main._fetch_yahoo_history("GC=F") is None


def test_fx_history_parses_timeseries():
    with patch.object(main.requests, "get", side_effect=fake_get):
        out = main._fetch_fx_history()
    assert out["GBP_USD"]["series"][-1] == {"date": "2026-11-13", "close": 1.3227}
    assert len(out["GBP_USD"]["series"]) == 5
    assert out["GBP_EUR"]["series"][0] == {"date": "2026-11-09", "close": 1.1986}
    assert out["EUR_USD"]["series"][-1] == {"date": "2026-11-13", "close": 1.1042}


def test_history_merges_all_eleven_assets():
    reset_history_cache()
    reset_finance_cache()
    with patch.object(main.requests, "get", side_effect=fake_get):
        history, _, from_cache = main.get_finance_history()
    assert not from_cache
    assert set(history) == {
        "Gold", "Silver", "Bitcoin", "Ethereum", "SP500", "FTSE100",
        "Brent_Oil", "GBP_USD", "GBP_EUR", "GBP_JPY", "EUR_USD",
    }
    gold = history["Gold"]
    assert gold["label"] == "Gold (per troy ounce)"
    assert gold["change"] == -228.2
    assert gold["change_pct"] == -5.55
    assert gold["day_high"] == 3927.2
    assert history["GBP_USD"]["previous_close"] == 1.3256
    assert history["GBP_USD"]["day_high"] is None
    assert history["GBP_USD"]["change"] == -0.0029
    # FP086.1: the four extra rows — view-only, with their own labels.
    assert history["Silver"]["label"] == "Silver (per troy ounce)"
    assert history["Ethereum"]["label"] == "Ethereum"
    assert history["FTSE100"]["label"] == "FTSE 100 index"
    assert history["GBP_JPY"]["label"] == "GBP/JPY"
    assert history["GBP_JPY"]["previous_close"] == 211.35
    assert history["GBP_JPY"]["change"] == 0.27
    assert history["GBP_JPY"]["change_pct"] == 0.13
    assert len(history["GBP_JPY"]["series"]) == 5


def test_history_prefers_stored_current_price():
    reset_history_cache()
    main._finance_cache["data"] = {"Gold": 3900.0}
    main._finance_cache["last_updated"] = 1
    try:
        with patch.object(main.requests, "get", side_effect=fake_get):
            history, _, _ = main.get_finance_history()
        assert history["Gold"]["current"] == 3900.0
        assert history["Gold"]["change"] == -214.5
    finally:
        main._finance_cache["data"] = {}
        main._finance_cache["last_updated"] = 0


def test_history_uses_cache_within_ttl():
    reset_history_cache()
    reset_finance_cache()
    calls = []

    def counting_get(url, **kwargs):
        calls.append(url)
        return fake_get(url, **kwargs)

    with patch.object(main.requests, "get", side_effect=counting_get):
        main.get_finance_history()
        first_call_count = len(calls)
        _, _, from_cache = main.get_finance_history()
    assert from_cache
    assert len(calls) == first_call_count
    assert first_call_count == 9  # 7 Yahoo + 2 Frankfurter


def test_history_serves_stale_cache_on_failure():
    reset_history_cache()
    stale = {"Gold": {"current": 3800.0, "label": "Gold (per troy ounce)"}}
    main._finance_history_cache["data"] = stale
    main._finance_history_cache["last_updated"] = 1  # long past the TTL
    with patch.object(main.requests, "get", side_effect=Exception("boom")):
        history, _, from_cache = main.get_finance_history()
    assert history == stale
    assert from_cache


def test_history_route_returns_json():
    reset_history_cache()
    reset_finance_cache()
    client = main.app.test_client()
    with patch.object(main.requests, "get", side_effect=fake_get):
        res = client.get("/api/finance/history")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["history"]["Gold"]["current"] == 3886.3
    assert data["cached"] is False
    reset_history_cache()
    with patch.object(main.requests, "get", side_effect=Exception("boom")):
        res = client.get("/api/finance/history")
    assert res.get_json()["success"] is False
