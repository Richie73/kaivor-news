"""
Kaivor Shopping Hub — price checks (FP125).

Generic price extraction from a product page: JSON-LD Product
offers first, then the og:price:amount / product:price:amount
meta tags. Only GBP prices are accepted. Anything else — a
bot wall, a page without structured data, a non-GBP price —
comes back as unavailable, and the stored price is left alone.
A failed check never invents a price.

Only items flagged checkable are ever fetched (see
shopping_store.py for why the Tapo triple and the Pixel deal
are not). Amazon and AliExpress block automated checks, so
their items are manual by design.
"""
from __future__ import annotations

import json
import re

import requests

_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 6a) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
)

_JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_META_PRICE_RE = re.compile(
    r'<meta[^>]+property=["\'](?:og:price:amount|product:price:amount)["\'][^>]+content=["\']([\d.]+)["\']',
    re.IGNORECASE,
)
_META_PRICE_RE_ALT = re.compile(
    r'<meta[^>]+content=["\']([\d.]+)["\'][^>]+property=["\'](?:og:price:amount|product:price:amount)["\']',
    re.IGNORECASE,
)


def _price_from_offers(offers):
    """A GBP price from a JSON-LD offers object, or None."""
    if isinstance(offers, list):
        for offer in offers:
            price = _price_from_offers(offer)
            if price is not None:
                return price
        return None
    if not isinstance(offers, dict):
        return None
    currency = offers.get("priceCurrency")
    if currency is not None and str(currency).upper() != "GBP":
        return None
    for key in ("price", "lowPrice"):
        value = offers.get(key)
        if value is None:
            continue
        try:
            price = float(str(value).replace(",", "").replace("£", ""))
        except ValueError:
            continue
        if price > 0:
            return price
    return None


def _price_from_json_ld(data):
    """Walk parsed JSON-LD looking for a Product's offers price."""
    if isinstance(data, list):
        for entry in data:
            price = _price_from_json_ld(entry)
            if price is not None:
                return price
        return None
    if not isinstance(data, dict):
        return None
    graph = data.get("@graph")
    if graph is not None:
        return _price_from_json_ld(graph)
    offers = data.get("offers")
    if offers is not None:
        price = _price_from_offers(offers)
        if price is not None:
            return price
    return None


def extract_price_from_html(html):
    """A GBP price from a product page's structured data, or None."""
    for block in _JSON_LD_RE.findall(html or ""):
        try:
            data = json.loads(block.strip())
        except (ValueError, TypeError):
            continue
        price = _price_from_json_ld(data)
        if price is not None:
            return price
    for pattern in (_META_PRICE_RE, _META_PRICE_RE_ALT):
        match = pattern.search(html or "")
        if match:
            try:
                price = float(match.group(1))
            except ValueError:
                continue
            if price > 0:
                return price
    return None


def check_price(url, timeout=15):
    """Fetch a product page and extract its GBP price.

    Returns {"status": "ok", "price": float} on success,
    {"status": "unavailable"} when the page loads but carries no
    usable price (including bot walls that return a 200 with no
    product data), and {"status": "error"} on a fetch failure.
    Only http(s) URLs are fetched.
    """
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return {"status": "error", "reason": "not a web address"}
    try:
        response = requests.get(
            url, timeout=timeout,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "en-GB"},
        )
    except requests.RequestException as exc:
        return {"status": "error", "reason": str(exc)[:120]}
    if response.status_code != 200:
        return {"status": "unavailable", "reason": f"HTTP {response.status_code}"}
    price = extract_price_from_html(response.text or "")
    if price is None:
        return {"status": "unavailable", "reason": "no price found on the page"}
    return {"status": "ok", "price": price}
