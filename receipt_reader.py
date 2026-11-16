"""Read a receipt photo with AI vision (OpenRouter).

FP102: the client sends a photo (data URL); this module sends it
to a vision model and returns the fields as a dict. The model is
configurable via KAIVOR_RECEIPT_MODEL; the default is
google/gemini-2.5-flash (verified on OpenRouter 15 Nov 2026 —
about $0.001 a scan at its listed prices).
"""
from __future__ import annotations

import json
import os
import re

import requests

DEFAULT_MODEL = "google/gemini-2.5-flash"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_IMAGE_CHARS = 6_000_000  # ~4.5MB of base64
ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp"}

PROMPT = (
    "Read this receipt and return ONLY a JSON object with these keys: "
    "merchant (the shop or business name, string or null), "
    "date (the purchase date as YYYY-MM-DD, string or null), "
    "total (the amount paid, number or null), "
    "vat (the VAT amount if shown, number or null), "
    "currency (the currency code, e.g. GBP, string or null). "
    "Use null for anything you cannot read clearly. Do not guess the total."
)


class ReceiptReadError(Exception):
    pass


def _coerce_money(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), 2)
    if isinstance(value, str):
        cleaned = value.replace("£", "").replace(",", "").strip()
        try:
            return round(float(cleaned), 2)
        except ValueError:
            return None
    return None


def _coerce_text(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def parse_receipt_json(text):
    """Extract the fields dict from a model reply (fences tolerated)."""
    if not isinstance(text, str):
        raise ReceiptReadError("The reader returned nothing usable.")
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.S)
    if match:
        cleaned = match.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ReceiptReadError("The reader returned nothing usable.")
        cleaned = cleaned[start:end + 1]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise ReceiptReadError("The reader returned nothing usable.")
    if not isinstance(data, dict):
        raise ReceiptReadError("The reader returned nothing usable.")
    return {
        "merchant": _coerce_text(data.get("merchant")),
        "date": _coerce_text(data.get("date")),
        "total": _coerce_money(data.get("total")),
        "vat": _coerce_money(data.get("vat")),
        "currency": _coerce_text(data.get("currency")) or "GBP",
    }


def read_receipt(image_data_url, api_key, model=None):
    if not api_key:
        raise ReceiptReadError("No OpenRouter key is set — save one in Settings first.")
    if not isinstance(image_data_url, str) or not image_data_url.startswith("data:image/"):
        raise ReceiptReadError("Send a receipt photo (JPEG, PNG or WebP).")
    media_type = image_data_url.split(";", 1)[0][5:]
    if media_type not in ALLOWED_MEDIA_TYPES:
        raise ReceiptReadError("Send a receipt photo (JPEG, PNG or WebP).")
    if len(image_data_url) > MAX_IMAGE_CHARS:
        raise ReceiptReadError("That photo is too large — try a smaller one (under ~4MB).")
    payload = {
        "model": model or os.environ.get("KAIVOR_RECEIPT_MODEL") or DEFAULT_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        }],
        "max_tokens": 400,
    }
    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
    except requests.RequestException:
        raise ReceiptReadError("Could not reach the reader — check the connection and try again.")
    if response.status_code != 200:
        raise ReceiptReadError("The reader refused the photo — try again.")
    try:
        data = response.json()
    except ValueError:
        raise ReceiptReadError("The reader returned nothing usable.")
    choices = data.get("choices") or []
    first = choices[0] if choices and isinstance(choices[0], dict) else {}
    content = (first.get("message") or {}).get("content")
    if not content:
        raise ReceiptReadError("The reader returned nothing usable.")
    return parse_receipt_json(content)
