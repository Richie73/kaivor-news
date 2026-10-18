"""Conservative structural validation and aggregate feed-quality diagnostics."""
from collections import Counter
from urllib.parse import urlparse


def article_rejection_reason(article):
    if not isinstance(article, dict):
        return "not_object"
    title = " ".join(str(article.get("title") or "").split())
    if not title or title.lower() in {"no title", "untitled"}:
        return "missing_title"
    link = str(article.get("link") or article.get("url") or "").strip()
    parsed = urlparse(link)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "invalid_link"
    return ""


def assess_feed(articles):
    """Return accepted articles plus safe aggregate diagnostics; never mutate input."""
    if not isinstance(articles, list):
        articles = []
    accepted = []
    rejected = Counter()
    categories = Counter()
    sources = Counter()
    seen = set()
    duplicates = 0
    for article in articles:
        reason = article_rejection_reason(article)
        if reason:
            rejected[reason] += 1
            continue
        item = dict(article)
        link = str(item.get("link") or item.get("url") or "").strip().lower()
        title = " ".join(str(item.get("title") or "").split()).lower()
        key = link if link and link != "#" else title
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        accepted.append(item)
        categories[str(item.get("category") or "Unknown").strip() or "Unknown"] += 1
        sources[str(item.get("source") or item.get("source_name") or "Unknown").strip() or "Unknown"] += 1
    return {
        "articles": accepted,
        "input_count": len(articles),
        "accepted_count": len(accepted),
        "rejected_count": sum(rejected.values()),
        "duplicate_count": duplicates,
        "rejection_reasons": dict(sorted(rejected.items())),
        "category_counts": dict(sorted(categories.items())),
        "source_counts": dict(sorted(sources.items())),
    }


def feed_quality_snapshot(articles):
    report = assess_feed(articles)
    report.pop("articles", None)
    return report
