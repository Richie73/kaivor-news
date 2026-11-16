"""FP100: RAMS drafting on a standard template.

The user describes the task and ticks the hazards that apply; the
AI drafts the method steps, risk rows (initial and residual
ratings) and PPE list, and the user reviews and edits every line
before saving. Saved RAMS print cleanly for site use. The hazard
library (rams_library) grounds the draft in standard groundworks
and civils controls; the drafter (rams_drafter) follows the chat
hub's provider chain (OpenRouter, then OpenAI).
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

import main
import news_store
import rams_drafter
from rams_drafter import RamsDraftError, build_draft_prompt, draft_rams, parse_rams_json
from rams_library import HAZARDS, hazard_by_id

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

NODE_ASSERTIONS = """
const assert = require('assert');
assert.equal(riskScore(4, 3), 12);
assert.equal(riskScore(5, 5), 25);
assert.deepEqual(riskBand(1), {label: 'Low', cls: 'risk-low'});
assert.deepEqual(riskBand(4), {label: 'Low', cls: 'risk-low'});
assert.deepEqual(riskBand(5), {label: 'Medium', cls: 'risk-medium'});
assert.deepEqual(riskBand(9), {label: 'Medium', cls: 'risk-medium'});
assert.deepEqual(riskBand(10), {label: 'High', cls: 'risk-high'});
assert.deepEqual(riskBand(16), {label: 'High', cls: 'risk-high'});
assert.deepEqual(riskBand(17), {label: 'Very high', cls: 'risk-very-high'});
assert.deepEqual(riskBand(25), {label: 'Very high', cls: 'risk-very-high'});
"""


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


# --- hazard library ---

def test_hazard_library_shape():
    assert len(HAZARDS) == 14
    for hazard in HAZARDS:
        assert hazard["id"] and hazard["name"] and hazard["who"]
        assert 1 <= hazard["severity"] <= 5
        assert 1 <= hazard["likelihood"] <= 5
        assert len(hazard["controls"]) >= 3
    assert hazard_by_id("excavation-collapse")["name"] == "Excavation collapse"
    assert hazard_by_id("no-such-hazard") is None


# --- draft parsing ---

def test_parse_rams_json_plain():
    draft = parse_rams_json(
        '{"method_steps": ["Set out the trench line.", "Excavate to formation."], '
        '"risks": [{"hazard": "Excavation collapse", "who": "Operatives", "severity": 5, '
        '"likelihood": 3, "residual_severity": 2, "residual_likelihood": 2, '
        '"controls": ["Batter the sides."]}], "ppe": ["Hard hat", "Hi-vis"]}'
    )
    assert draft["method_steps"] == ["Set out the trench line.", "Excavate to formation."]
    assert draft["risks"][0]["severity"] == 5
    assert draft["risks"][0]["residual_severity"] == 2
    assert draft["ppe"] == ["Hard hat", "Hi-vis"]


def test_parse_rams_json_clamps_ratings_and_skips_bad_rows():
    draft = parse_rams_json(
        '```json\n{"method_steps": [], "risks": ['
        '{"hazard": "Noise", "severity": 9, "likelihood": 0, "residual_severity": "x", "residual_likelihood": null, "controls": []}, '
        '{"who": "Nobody"}], "ppe": []}\n```'
    )
    assert len(draft["risks"]) == 1
    assert draft["risks"][0]["severity"] == 5
    assert draft["risks"][0]["likelihood"] == 1
    assert draft["risks"][0]["residual_severity"] == 3


def test_parse_rams_json_rejects_garbage():
    with pytest.raises(RamsDraftError):
        parse_rams_json("no rams here")
    with pytest.raises(RamsDraftError):
        parse_rams_json(None)


# --- prompt building ---

def test_build_draft_prompt_includes_selected_hazards():
    prompt = build_draft_prompt(
        "Lay drainage", "Plot 12", ["excavation-collapse", "no-such-hazard"],
        "3t digger", "Live footpath alongside",
    )
    assert "Task: Lay drainage" in prompt
    assert "Site: Plot 12" in prompt
    assert "Plant and equipment: 3t digger" in prompt
    assert "Live footpath alongside" in prompt
    assert "Excavation collapse" in prompt
    assert "Batter or step the sides" in prompt
    assert "no-such-hazard" not in prompt


def test_build_draft_prompt_without_hazards():
    prompt = build_draft_prompt("Jet wash the yard", "", [], "", "")
    assert "No hazards were ticked" in prompt


# --- drafting ---

def test_draft_rams_calls_openrouter_first(monkeypatch):
    reply = {"choices": [{"message": {"content": '{"method_steps": ["Step one."], "risks": [], "ppe": ["Gloves"]}'}}]}
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-1")
    monkeypatch.setenv("OPENAI_API_KEY", "key-2")
    with patch.object(requests, "post", return_value=FakeResponse(200, reply)) as post:
        draft = draft_rams("Lay drainage", "Plot 12", ["excavation-collapse"], "", "")
    assert draft["method_steps"] == ["Step one."]
    assert draft["ppe"] == ["Gloves"]
    _, kwargs = post.call_args
    assert kwargs["json"]["model"] == "deepseek/deepseek-chat"
    assert "Excavation collapse" in kwargs["json"]["messages"][1]["content"]


def test_draft_rams_falls_back_to_openai(monkeypatch):
    reply = {"choices": [{"message": {"content": '{"method_steps": ["Step one."], "risks": [], "ppe": []}'}}]}
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-1")
    monkeypatch.setenv("OPENAI_API_KEY", "key-2")
    calls = []
    with patch.object(requests, "post", side_effect=[FakeResponse(500, {}), FakeResponse(200, reply)]) as post:
        draft = draft_rams("Lay drainage", "", [], "", "")
    assert draft["method_steps"] == ["Step one."]
    assert post.call_count == 2
    assert post.call_args[1]["json"]["model"] == "gpt-4o-mini"


def test_draft_rams_without_keys(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with pytest.raises(RamsDraftError):
        draft_rams("Lay drainage", "", [], "", "")


# --- store ---

def test_rams_store_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(news_store, "RAMS_FILE", tmp_path / "rams.json")
    assert news_store.load_rams_list() == []
    saved = news_store.save_rams({
        "task": "Lay drainage", "site": "Plot 12", "date": "2026-11-15",
        "method_steps": ["Step one."], "risks": [], "ppe": ["Gloves"],
    })
    assert saved["id"].startswith("rams-")
    assert saved["prepared_by"] == "Richard Gallagher"
    assert saved["company"] == "Gallagher Construction Services"
    assert news_store.get_rams(saved["id"])["task"] == "Lay drainage"
    updated = news_store.update_rams(saved["id"], {**saved, "task": "Lay drainage (revised)"})
    assert updated["task"] == "Lay drainage (revised)"
    assert updated["created"] == saved["created"]
    assert news_store.remove_rams(saved["id"]) is True
    assert news_store.load_rams_list() == []
    assert news_store.remove_rams(saved["id"]) is False


# --- routes ---

def test_rams_hazards_route_is_open():
    client = main.app.test_client()
    response = client.get("/api/rams/hazards")
    assert response.status_code == 200
    assert len(response.get_json()["hazards"]) == 14


def test_rams_draft_route(authed_client):
    draft = {"method_steps": ["Step one."], "risks": [], "ppe": ["Gloves"]}
    with patch.object(main, "draft_rams", return_value=draft) as drafter:
        response = authed_client.post("/api/rams/draft", json={
            "task": "Lay drainage", "site": "Plot 12", "plant": "3t digger",
            "notes": "", "hazard_ids": ["excavation-collapse"],
        })
    assert response.status_code == 200
    assert response.get_json()["draft"]["task"] == "Lay drainage"
    assert response.get_json()["draft"]["site"] == "Plot 12"
    drafter.assert_called_once()
    response = authed_client.post("/api/rams/draft", json={"task": "  "})
    assert response.status_code == 400


def test_rams_save_get_update_delete_round_trip(authed_client):
    rams = {"task": "Lay drainage", "site": "Plot 12", "method_steps": ["Step one."], "risks": [], "ppe": []}
    saved = {**rams, "id": "rams-1", "created": "2026-11-15T00:00:00", "updated": "2026-11-15T00:00:00"}
    with patch.object(main, "save_rams", return_value=saved):
        response = authed_client.post("/api/rams", json={"rams": rams})
    assert response.status_code == 200
    assert response.get_json()["rams"]["id"] == "rams-1"
    with patch.object(main, "load_rams_list", return_value=[saved]):
        response = authed_client.get("/api/rams")
    assert response.get_json()["count"] == 1
    with patch.object(main, "get_rams", return_value=saved):
        response = authed_client.get("/api/rams/rams-1")
    assert response.status_code == 200
    with patch.object(main, "get_rams", return_value=None):
        response = authed_client.get("/api/rams/rams-missing")
    assert response.status_code == 404
    with patch.object(main, "update_rams", return_value={**saved, "task": "Revised"}):
        response = authed_client.put("/api/rams/rams-1", json={"rams": {**rams, "task": "Revised"}})
    assert response.get_json()["rams"]["task"] == "Revised"
    with patch.object(main, "remove_rams", return_value=True):
        response = authed_client.delete("/api/rams/rams-1")
    assert response.get_json()["success"] is True
    response = authed_client.post("/api/rams", json={"rams": {"site": "Plot 12"}})
    assert response.status_code == 400


def test_rams_mutations_are_pin_guarded():
    assert "api_rams_draft" in main._GUARDED_MUTATION_ENDPOINTS
    assert "api_rams_save" in main._GUARDED_MUTATION_ENDPOINTS
    assert "api_rams_update" in main._GUARDED_MUTATION_ENDPOINTS
    assert "api_rams_remove" in main._GUARDED_MUTATION_ENDPOINTS
    client = main.app.test_client()
    assert client.post("/api/rams/draft", json={"task": "X"}).status_code in {401, 503}
    assert client.post("/api/rams", json={"rams": {"task": "X"}}).status_code in {401, 503}
    assert client.put("/api/rams/rams-1", json={"rams": {"task": "X"}}).status_code in {401, 503}
    assert client.delete("/api/rams/rams-1").status_code in {401, 503}


# --- template ---

def test_rams_view_and_hub_button():
    html = template_text()
    assert 'onclick="showRams()">📋 Draft a RAMS</button>' in html
    body = function_body(html, "showRams")
    assert "hideWeatherView();" in body
    assert "hideMarketsView();" in body
    assert "hideMorningHubView();" in body
    assert "cacheNewsContainer();" in body
    assert 'id="rams-hazards"' in body
    assert "generateRamsDraft()" in body
    assert 'id="rams-editor"' in body
    assert "loadRamsList();" in body


def test_rams_print_document():
    html = template_text()
    assert '<div id="rams-print-doc"></div>' in html
    assert "@media print" in html
    assert "#rams-print-doc, #rams-print-doc * { visibility:visible; }" in html
    body = function_body(html, "ramsPrintHtml")
    assert "Risk Assessment &amp; Method Statement" in body
    assert "Method statement" in body
    assert "Risk assessment" in body
    assert "Sign-off" in body
    assert "Draft — review and sign off before use." in body
    assert "Accepted by (site manager)" in body


def test_risk_band_runs_under_node():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    html = template_text()
    score = re.search(r"function riskScore\(severity, likelihood\) \{.*?\n\}", html, re.S)
    band = re.search(r"function riskBand\(score\) \{.*?\n\}", html, re.S)
    assert score and band
    script = score.group(0) + "\n" + band.group(0) + "\n" + NODE_ASSERTIONS
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
        handle.write(script)
        path = handle.name
    result = subprocess.run([node, path], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
