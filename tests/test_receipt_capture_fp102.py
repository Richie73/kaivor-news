"""FP102: receipt capture — scan a receipt photo, save the expense.

The client sends a photo (data URL) to POST /api/receipts/scan,
which reads it with AI vision through OpenRouter
(google/gemini-2.5-flash by default, ~$0.001 a scan) and returns
the fields for the user to check. Nothing saves until the user
taps Save (POST /api/receipts). Receipts live in the same
file-store pattern as saved articles (data/receipts.json), list
via GET /api/receipts, delete via DELETE, and download as a CSV
from the client. Scan/save/delete are PIN-gated; listing is an
open read.
"""
import re
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

import main
import news_store
import receipt_reader
from receipt_reader import ReceiptReadError, parse_receipt_json, read_receipt

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

TINY_JPEG = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        # FP108: the provider layer calls this like a real Response.
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def function_body(html, name):
    match = re.search(rf"function {name}\(.*?\n\}}", html, re.S)
    assert match, f"{name} missing"
    return match.group(0)


# --- reader parsing ---

def test_parse_receipt_json_plain():
    fields = parse_receipt_json(
        '{"merchant": "Toolstation", "date": "2026-11-10", '
        '"total": 12.06, "vat": 2.01, "currency": "GBP"}'
    )
    assert fields == {
        "merchant": "Toolstation", "date": "2026-11-10",
        "total": 12.06, "vat": 2.01, "currency": "GBP",
    }


def test_parse_receipt_json_fenced_and_string_money():
    fields = parse_receipt_json(
        'Here it is:\n```json\n{"merchant": "Screwfix", "date": null, '
        '"total": "£139.99", "vat": "23.33", "currency": null}\n```'
    )
    assert fields["merchant"] == "Screwfix"
    assert fields["date"] is None
    assert fields["total"] == 139.99
    assert fields["vat"] == 23.33
    assert fields["currency"] == "GBP"


def test_parse_receipt_json_rejects_garbage():
    with pytest.raises(ReceiptReadError):
        parse_receipt_json("no receipt here")
    with pytest.raises(ReceiptReadError):
        parse_receipt_json(None)


# --- reader request ---

def test_read_receipt_posts_image_to_openrouter(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-123")
    reply = {"choices": [{"message": {"content": '{"merchant": "B&Q", "date": "2026-11-15", "total": 27.02, "vat": null, "currency": "GBP"}'}}]}
    with patch.object(requests, "post", return_value=FakeResponse(200, reply)) as post:
        fields = read_receipt(TINY_JPEG)
    assert fields["merchant"] == "B&Q"
    assert fields["total"] == 27.02
    _, kwargs = post.call_args
    assert kwargs["json"]["model"] == "google/gemini-2.5-flash"
    content = kwargs["json"]["messages"][0]["content"]
    assert content[1]["image_url"]["url"] == TINY_JPEG
    assert kwargs["headers"]["Authorization"] == "Bearer key-123"


def test_read_receipt_rejects_bad_inputs(monkeypatch):
    # FP108: the key comes from the environment now, not an argument.
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ReceiptReadError):
        read_receipt(TINY_JPEG)
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-123")
    with pytest.raises(ReceiptReadError):
        read_receipt("not-a-data-url")
    with pytest.raises(ReceiptReadError):
        read_receipt("data:image/gif;base64,AAAA")
    with pytest.raises(ReceiptReadError):
        read_receipt("data:image/jpeg;base64," + "A" * 6_000_000)


def test_read_receipt_refusal_is_a_clean_error(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-123")
    with patch.object(requests, "post", return_value=FakeResponse(402, {})):
        with pytest.raises(ReceiptReadError):
            read_receipt(TINY_JPEG)


# --- store ---

def test_receipt_store_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(news_store, "RECEIPTS_FILE", tmp_path / "receipts.json")
    assert news_store.load_receipts() == []
    saved = news_store.save_receipt({"merchant": "Toolstation", "date": "2026-11-10", "total": 12.06, "vat": 2.01, "currency": "GBP"})
    assert saved["id"].startswith("rcpt-")
    assert saved["added"]
    assert len(news_store.load_receipts()) == 1
    assert news_store.remove_receipt(saved["id"]) is True
    assert news_store.load_receipts() == []
    assert news_store.remove_receipt(saved["id"]) is False


# --- routes ---

def test_receipt_routes_round_trip(authed_client, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-123")
    fields = {"merchant": "Toolstation", "date": "2026-11-10", "total": 12.06, "vat": 2.01, "currency": "GBP"}
    with patch.object(main, "read_receipt", return_value=fields) as reader:
        response = authed_client.post("/api/receipts/scan", json={"image": TINY_JPEG})
    assert response.status_code == 200
    assert response.get_json() == {"success": True, "fields": fields}
    reader.assert_called_once()

    with patch.object(main, "save_receipt", return_value={**fields, "id": "rcpt-1"}) as saver:
        response = authed_client.post("/api/receipts", json={"receipt": fields})
    assert response.status_code == 200
    assert response.get_json()["receipt"]["id"] == "rcpt-1"
    saver.assert_called_once()

    with patch.object(main, "load_receipts", return_value=[{**fields, "id": "rcpt-1"}]):
        response = authed_client.get("/api/receipts")
    assert response.status_code == 200
    assert response.get_json()["count"] == 1
    assert response.get_json()["total"] == 12.06

    with patch.object(main, "remove_receipt", return_value=True):
        response = authed_client.delete("/api/receipts/rcpt-1")
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_receipt_routes_validate_input(authed_client):
    response = authed_client.post("/api/receipts/scan", json={})
    assert response.status_code == 400
    response = authed_client.post("/api/receipts", json={"receipt": {"merchant": "X"}})
    assert response.status_code == 400
    response = authed_client.post("/api/receipts", json={})
    assert response.status_code == 400


def test_receipt_scan_reader_failure_is_502(authed_client, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-123")
    with patch.object(main, "read_receipt", side_effect=ReceiptReadError("The reader refused the photo — try again.")):
        response = authed_client.post("/api/receipts/scan", json={"image": TINY_JPEG})
    assert response.status_code == 502
    assert "refused" in response.get_json()["error"]


def test_receipt_mutations_are_pin_guarded():
    assert "api_receipt_scan" in main._GUARDED_MUTATION_ENDPOINTS
    assert "api_receipt_save" in main._GUARDED_MUTATION_ENDPOINTS
    assert "api_receipt_remove" in main._GUARDED_MUTATION_ENDPOINTS
    client = main.app.test_client()
    response = client.post("/api/receipts/scan", json={"image": TINY_JPEG})
    assert response.status_code in {401, 503}
    response = client.post("/api/receipts", json={"receipt": {"total": 1.0}})
    assert response.status_code in {401, 503}
    response = client.delete("/api/receipts/rcpt-1")
    assert response.status_code in {401, 503}


# --- template ---

def test_receipts_view_and_hub_button():
    html = template_text()
    assert 'onclick="showReceipts()">🧾 Scan a receipt</button>' in html
    body = function_body(html, "showReceipts")
    assert "hideWeatherView();" in body
    assert "hideMarketsView();" in body
    assert "hideMorningHubView();" in body
    assert "cacheNewsContainer();" in body
    assert 'id="receipt-file" accept="image/*" capture="environment"' in body
    assert 'id="receipt-edit"' in body
    assert "loadReceipts();" in body
    assert "downloadReceiptsCsv()" in body
    assert "kaivor-receipts.csv" in html
