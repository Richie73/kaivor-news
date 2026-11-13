"""Publisher-aware links for a personal subscription reader. No scraping."""
from urllib.parse import urlparse

PUBLISHERS = {
    "nytimes.com": {"label": "The New York Times", "access_label": "Open with your NYT subscription"},
    "telegraph.co.uk": {"label": "The Telegraph", "access_label": "Open with your Telegraph subscription"},
    "independent.co.uk": {"label": "The Independent", "access_label": "Open with your Independent subscription"},
    "theathletic.com": {"label": "The Athletic", "access_label": "Open with your Athletic subscription"},
}

FREEDIUM_MIRROR_BASE = "https://freedium-mirror.cfd"

# Publishers the Freedium Mirror service can render. Freedium is a third-party
# reader: Kaivor never sends credentials, cookies or payment details there,
# only the article URL.
FREEDIUM_DOMAINS = {
    "medium.com": "Medium",
    "nytimes.com": "The New York Times",
    "washingtonpost.com": "The Washington Post",
    "bloomberg.com": "Bloomberg",
    "reuters.com": "Reuters",
    "economist.com": "The Economist",
    "ft.com": "Financial Times",
}


def freedium_domain_for_url(url):
    """Match only known Freedium domains or their subdomains."""
    try:
        parsed = urlparse(str(url or ""))
        if parsed.scheme not in {"http", "https"}:
            return None
        host = (parsed.hostname or "").lower().rstrip(".")
    except (TypeError, ValueError):
        return None
    for domain, label in FREEDIUM_DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return {"domain": domain, "label": label}
    return None


def freedium_url_for(url):
    """Return the Freedium Mirror URL for a supported article, else None."""
    if not freedium_domain_for_url(url):
        return None
    clean = str(url or "").strip()
    if not clean or len(clean) > 2048:
        return None
    return FREEDIUM_MIRROR_BASE + "/" + clean


def freedium_access_info(url=""):
    """Return Freedium unlock metadata for a URL (link only; no fetch here)."""
    mirror = freedium_url_for(url)
    if not mirror:
        return {"available": False, "url": "", "label": "Unlock via Freedium"}
    return {"available": True, "url": mirror, "label": "Unlock via Freedium"}


def publisher_for_url(url):
    """Match only known publisher domains or their subdomains."""
    try:
        host = (urlparse(str(url or "")).hostname or "").lower().rstrip(".")
    except (TypeError, ValueError):
        return None
    # The Athletic's current RSS may link through the NYT-owned /athletic/ path.
    # Check this before the broader nytimes.com match so the label remains correct.
    path = (urlparse(str(url or "")).path or "").lower()
    if host == "nytimes.com" or host.endswith(".nytimes.com"):
        if path.startswith("/athletic/") or path == "/athletic":
            return {
                "domain": "theathletic.com",
                **PUBLISHERS["theathletic.com"],
            }
    for domain, info in PUBLISHERS.items():
        if host == domain or host.endswith("." + domain):
            return {"domain": domain, **info}
    return None


def publisher_access_info(source="", url=""):
    """Return publisher access metadata using URL as the source of truth."""
    info = publisher_for_url(url)
    if not info:
        return {"supported": False, "publisher": "", "label": "Open original article"}
    return {"supported": True, "publisher": info["label"], "label": info["access_label"]}
