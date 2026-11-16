"""FP105: Readwise highlights sync (export API v2).

Pulls the user's highlights into Kaivor's Reading tab via the
Readwise export endpoint (GET https://readwise.io/api/v2/export/),
which returns books with their highlights in one call, paged by
pageCursor. Read-only: Kaivor never creates, edits or deletes
highlights. Auth is a Readwise access token (readwise.io/access_token)
in KAIVOR_READWISE_TOKEN — a dashboard secret, never pasted in chat.

The sync stores the newest 500 highlights (the export can return a
whole library; the Reading tab shows recent highlights, not an
archive). Deleted and discarded highlights are skipped.
"""

import time

import requests

EXPORT_URL = "https://readwise.io/api/v2/export/"

MAX_PAGES = 10
MAX_HIGHLIGHTS = 500


class ReadwiseError(Exception):
    """The Readwise export call failed (network, auth or bad data)."""


def fetch_export_page(token, page_cursor=None, timeout=30):
    """One export page. Raises ReadwiseError on any failure."""
    params = {}
    if page_cursor:
        params["pageCursor"] = page_cursor
    try:
        response = requests.get(
            EXPORT_URL,
            headers={"Authorization": f"Token {token}"},
            params=params,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise ReadwiseError(f"Could not reach Readwise ({exc}).") from exc
    if response.status_code == 401:
        raise ReadwiseError("Readwise refused the access token.")
    if response.status_code != 200:
        raise ReadwiseError(f"Readwise returned HTTP {response.status_code}.")
    try:
        data = response.json()
    except ValueError as exc:
        raise ReadwiseError("Readwise returned nothing usable.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ReadwiseError("Readwise returned nothing usable.")
    return data


def flatten_export(results):
    """Books-with-highlights -> flat highlight dicts, newest first."""
    highlights = []
    for book in results or []:
        if not isinstance(book, dict) or book.get("is_deleted"):
            continue
        title = (book.get("title") or "").strip()
        author = (book.get("author") or "").strip()
        category = (book.get("category") or "").strip()
        for item in book.get("highlights") or []:
            if not isinstance(item, dict):
                continue
            if item.get("is_deleted") or item.get("is_discard"):
                continue
            text = (item.get("text") or "").strip()
            if not text:
                continue
            highlights.append(
                {
                    "id": item.get("id"),
                    "text": text,
                    "note": (item.get("note") or "").strip() or None,
                    "color": (item.get("color") or "").strip() or None,
                    "title": title,
                    "author": author,
                    "category": category,
                    "highlighted_at": item.get("highlighted_at"),
                    "updated_at": item.get("updated_at"),
                    "readwise_url": item.get("readwise_url"),
                    "tags": [t for t in (item.get("tags") or []) if isinstance(t, dict)],
                    "is_favorite": bool(item.get("is_favorite")),
                }
            )
    highlights.sort(key=lambda h: h.get("updated_at") or h.get("highlighted_at") or "", reverse=True)
    return highlights


def fetch_all_highlights(token, max_pages=MAX_PAGES):
    """Follow pageCursor to the end (or the page cap).

    Returns (highlights, complete): complete is False when pages
    remained after max_pages — the caller says so in the UI.
    """
    all_highlights = []
    cursor = None
    complete = True
    for _ in range(max_pages):
        page = fetch_export_page(token, page_cursor=cursor)
        all_highlights.extend(flatten_export(page.get("results")))
        cursor = page.get("nextPageCursor")
        if not cursor:
            break
    else:
        complete = False
    # Pages are not guaranteed to arrive in date order, so sort the
    # combined list before the caller caps it to the newest 500.
    all_highlights.sort(
        key=lambda h: h.get("updated_at") or h.get("highlighted_at") or "", reverse=True
    )
    return all_highlights, complete


def sync_highlights(token):
    """Full sync: fetch, cap to the newest 500, return the payload."""
    highlights, complete = fetch_all_highlights(token)
    total = len(highlights)
    return {
        "highlights": highlights[:MAX_HIGHLIGHTS],
        "last_sync": int(time.time()),
        "total": total,
        "complete": complete,
    }
