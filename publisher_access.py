"""Publisher-aware links for a personal subscription reader. No scraping."""
from urllib.parse import urlparse

PUBLISHERS = {
    "nytimes.com": {"label": "The New York Times", "access_label": "Open with your NYT subscription"},
    "telegraph.co.uk": {"label": "The Telegraph", "access_label": "Open with your Telegraph subscription"},
    "independent.co.uk": {"label": "The Independent", "access_label": "Open with your Independent subscription"},
    "theathletic.com": {"label": "The Athletic", "access_label": "Open with your Athletic subscription"},
}


def publisher_for_url(url):
    """Match only known publisher domains or their subdomains."""
    try:
        host = (urlparse(str(url or "")).hostname or "").lower().rstrip(".")
    except (TypeError, ValueError):
        return None
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
