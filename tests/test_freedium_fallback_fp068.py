"""FP068 tests for the Freedium Mirror fallback in article extraction.

FP068.1: a direct HTTP 403 is also retried through the mirror (live check:
FT refuses the direct fetch while the mirror serves the full article).
Other HTTP errors are still not retried.
"""
from unittest.mock import Mock, patch

import article_extractor

MIRROR_BASE = "https://freedium-mirror.cfd"

PAYWALL_HTML = (
    "<html><body><div class=\"paywall\">Subscribe to continue reading</div>"
    "<p>Short teaser sentence about the story.</p></body></html>"
)

MIRROR_HTML = (
    "<html><main><article><h1>Full story</h1><p>"
    + ("The full article text continues here. " * 30)
    + "</p></article></main></html>"
)

# Mirror rendering without article/main tags: only the .prose container.
PROSE_HTML = (
    "<html><body><div class=\"prose\"><h1>Full story</h1><p>"
    + ("The full article text continues here. " * 30)
    + "</p></div></body></html>"
)


def _response(html, status=200, content_type="text/html; charset=utf-8", headers=None):
    response = Mock()
    response.status_code = status
    response.headers = {"Content-Type": content_type, **(headers or {})}
    response.encoding = "utf-8"
    response.iter_content.return_value = [html.encode("utf-8")]
    response.close = Mock()
    return response


def test_freedium_fallback_unlocks_paywalled_article():
    url = "https://www.nytimes.com/2026/11/12/world/story.html"
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", side_effect=[_response(PAYWALL_HTML), _response(MIRROR_HTML)]) as get:
        result = article_extractor.extract_article_text(url)
    assert result["success"] is True
    assert "The full article text" in result["text"]
    assert result["content_source"] == "freedium_mirror"
    assert result["via_freedium"] is True
    assert result["final_url"] == MIRROR_BASE + "/" + url
    assert get.call_count == 2
    assert get.call_args_list[0][0][0] == url
    assert get.call_args_list[1][0][0] == MIRROR_BASE + "/" + url


def test_mirror_failure_returns_original_failure():
    url = "https://www.bloomberg.com/news/articles/story"
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", side_effect=[_response(PAYWALL_HTML), _response(PAYWALL_HTML)]) as get:
        result = article_extractor.extract_article_text(url)
    assert result["success"] is False
    assert result["status"] == "extraction_failed"
    assert result.get("via_freedium") is not True
    assert get.call_count == 2


def test_direct_success_never_calls_mirror():
    url = "https://www.nytimes.com/2026/11/12/world/story.html"
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response(MIRROR_HTML)) as get:
        result = article_extractor.extract_article_text(url)
    assert result["success"] is True
    assert result["via_freedium"] is False
    assert result["content_source"] == "semantic_container"
    assert get.call_count == 1


def test_non_freedium_domain_never_retried():
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response(PAYWALL_HTML)) as get:
        result = article_extractor.extract_article_text("https://example.com/story")
    assert result["success"] is False
    assert result["status"] == "extraction_failed"
    assert get.call_count == 1


def test_attacker_domain_never_retried():
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response(PAYWALL_HTML)) as get:
        result = article_extractor.extract_article_text("https://nytimes.com.attacker.example/story")
    assert result["success"] is False
    assert result["status"] == "extraction_failed"
    assert get.call_count == 1


def test_subdomain_is_supported():
    url = "https://www.washingtonpost.com/world/story"
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", side_effect=[_response(PAYWALL_HTML), _response(MIRROR_HTML)]) as get:
        result = article_extractor.extract_article_text(url)
    assert result["success"] is True
    assert result["via_freedium"] is True
    assert get.call_args_list[1][0][0] == MIRROR_BASE + "/" + url


def test_http_403_is_retried_through_mirror():
    url = "https://www.ft.com/content/story"
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", side_effect=[_response("", status=403), _response(MIRROR_HTML)]) as get:
        result = article_extractor.extract_article_text(url)
    assert result["success"] is True
    assert "The full article text" in result["text"]
    assert result["content_source"] == "freedium_mirror"
    assert result["via_freedium"] is True
    assert result["final_url"] == MIRROR_BASE + "/" + url
    assert get.call_count == 2
    assert get.call_args_list[0][0][0] == url
    assert get.call_args_list[1][0][0] == MIRROR_BASE + "/" + url


def test_http_403_mirror_failure_returns_original():
    url = "https://www.economist.com/business/story"
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", side_effect=[_response("", status=403), _response(PAYWALL_HTML)]) as get:
        result = article_extractor.extract_article_text(url)
    assert result["success"] is False
    assert result["status"] == "http_error"
    assert result["http_status"] == 403
    assert result.get("via_freedium") is not True
    assert get.call_count == 2


def test_http_404_is_not_retried():
    url = "https://www.ft.com/content/story"
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response("", status=404)) as get:
        result = article_extractor.extract_article_text(url)
    assert result["success"] is False
    assert result["status"] == "http_error"
    assert result["http_status"] == 404
    assert get.call_count == 1


def test_http_403_non_freedium_domain_not_retried():
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response("", status=403)) as get:
        result = article_extractor.extract_article_text("https://example.com/story")
    assert result["success"] is False
    assert result["status"] == "http_error"
    assert get.call_count == 1


def test_mirror_prose_container_extracts():
    url = "https://medium.com/@author/story-123"
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", side_effect=[_response(PAYWALL_HTML), _response(PROSE_HTML)]):
        result = article_extractor.extract_article_text(url)
    assert result["success"] is True
    assert result["via_freedium"] is True
    assert "The full article text" in result["text"]


def test_mirror_url_is_validated():
    url = "https://www.economist.com/business/story"
    with patch.object(article_extractor, "_validate_public_url", side_effect=[(True, ""), (True, "")]) as validate, \
         patch.object(article_extractor.requests, "get", side_effect=[_response(PAYWALL_HTML), _response(MIRROR_HTML)]):
        result = article_extractor.extract_article_text(url)
    assert result["success"] is True
    assert validate.call_count == 2
    assert validate.call_args_list[0][0][0] == url
    assert validate.call_args_list[1][0][0] == MIRROR_BASE + "/" + url
