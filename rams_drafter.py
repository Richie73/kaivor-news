"""Draft a RAMS with AI (FP100).

The user describes the task and ticks the hazards that apply; the
selected hazards' standard controls (rams_library) go into the
prompt as the starting point, and the model drafts the method
statement steps, the risk rows (initial and residual ratings)
and the PPE list as JSON. The user reviews and edits every line
in the app before anything is saved or printed — the draft is
never used as-is.

Provider chain follows the chat hub: OpenRouter first
(deepseek/deepseek-chat), OpenAI (gpt-4o-mini) as fallback.
"""
from __future__ import annotations

import json
import os
import re

import requests

from rams_library import hazard_by_id

PROVIDERS = [
    ("openrouter", "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", "deepseek/deepseek-chat"),
    ("openai", "https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY", "gpt-4o-mini"),
]

SYSTEM_PROMPT = (
    "You are drafting a UK construction Risk Assessment and Method Statement (RAMS) "
    "for a groundworks and civils contractor. Use plain, practical site language. "
    "Return ONLY a JSON object with these keys: "
    "method_steps (a list of short numbered work steps in order, 5-15 steps), "
    "risks (a list of objects, one per hazard, each with hazard, who, severity (1-5), "
    "likelihood (1-5), residual_severity (1-5), residual_likelihood (1-5) and controls "
    "(a list of 2-5 short control measures)), "
    "ppe (a list of PPE items for the task). "
    "Base the risks on the hazards supplied. Residual ratings must be lower than the "
    "initial ratings where the controls are effective. Do not invent site-specific "
    "facts you were not given. Keep every step and control to one sentence."
)


class RamsDraftError(Exception):
    pass


def _clamp_rating(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 3
    return max(1, min(5, number))


def _clean_lines(value, cap):
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    return cleaned[:cap]


def parse_rams_json(text):
    """Extract the draft dict from a model reply (fences tolerated)."""
    if not isinstance(text, str):
        raise RamsDraftError("The drafter returned nothing usable.")
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.S)
    if match:
        cleaned = match.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RamsDraftError("The drafter returned nothing usable.")
        cleaned = cleaned[start:end + 1]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise RamsDraftError("The drafter returned nothing usable.")
    if not isinstance(data, dict):
        raise RamsDraftError("The drafter returned nothing usable.")
    risks = []
    for row in data.get("risks") or []:
        if not isinstance(row, dict) or not str(row.get("hazard") or "").strip():
            continue
        risks.append({
            "hazard": str(row["hazard"]).strip(),
            "who": str(row.get("who") or "Operatives").strip(),
            "severity": _clamp_rating(row.get("severity")),
            "likelihood": _clamp_rating(row.get("likelihood")),
            "residual_severity": _clamp_rating(row.get("residual_severity")),
            "residual_likelihood": _clamp_rating(row.get("residual_likelihood")),
            "controls": _clean_lines(row.get("controls"), 8),
        })
    return {
        "method_steps": _clean_lines(data.get("method_steps"), 30),
        "risks": risks[:20],
        "ppe": _clean_lines(data.get("ppe"), 12),
    }


def build_draft_prompt(task, site, hazard_ids, plant, notes):
    parts = [f"Task: {task}"]
    if site:
        parts.append(f"Site: {site}")
    if plant:
        parts.append(f"Plant and equipment: {plant}")
    if notes:
        parts.append(f"Notes: {notes}")
    hazards = [hazard_by_id(hazard_id) for hazard_id in (hazard_ids or [])]
    hazards = [hazard for hazard in hazards if hazard]
    if hazards:
        lines = ["Hazards that apply (with their standard controls as a starting point):"]
        for hazard in hazards:
            lines.append(
                f"- {hazard['name']} (who: {hazard['who']}; "
                f"typical severity {hazard['severity']}, likelihood {hazard['likelihood']}): "
                + "; ".join(hazard["controls"])
            )
        parts.append("\n".join(lines))
    else:
        parts.append("No hazards were ticked — include the hazards a competent person would expect for this task.")
    return "\n\n".join(parts)


def draft_rams(task, site, hazard_ids, plant, notes):
    if not isinstance(task, str) or not task.strip():
        raise RamsDraftError("Describe the task first.")
    prompt = build_draft_prompt(task.strip(), site, hazard_ids, plant, notes)
    last_error = None
    for _name, url, env_key, model in PROVIDERS:
        api_key = os.environ.get(env_key)
        if not api_key:
            continue
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 2500,
                },
                timeout=90,
            )
        except requests.RequestException as error:
            last_error = error
            continue
        if response.status_code != 200:
            last_error = RuntimeError(f"provider returned {response.status_code}")
            continue
        try:
            data = response.json()
        except ValueError:
            last_error = ValueError("bad provider JSON")
            continue
        choices = data.get("choices") or []
        first = choices[0] if choices and isinstance(choices[0], dict) else {}
        content = (first.get("message") or {}).get("content")
        if not content:
            last_error = ValueError("empty provider reply")
            continue
        return parse_rams_json(content)
    if last_error is not None:
        raise RamsDraftError("The drafter could not reach the AI — check the connection and try again.")
    raise RamsDraftError("No AI key is set — save an OpenRouter or OpenAI key in Settings first.")
