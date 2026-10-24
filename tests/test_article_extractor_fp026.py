"""FP026 tests for bounded, public-URL article retrieval."""
from unittest.mock import Mock, patch

import article_extractor


def _response(html, status=200, content_type="text/html; charset=utf-8", headers=None):
    response = Mock()
    response.status_code = status
    response.headers = {"Content-Type": content_type, **(headers or {})}
    response.encoding = "utf-8"
    response.iter_content.return_value = [html.encode("utf-8")]
    response.close = Mock()
    return response


def test_extracts_readable_article_and_ignores_script_and_navigation():
    html = (
        "<html><nav>MENU " + ("navigation " * 100) + "</nav>"
        "<main><article><h1>Road funding</h1><p>" + ("Road repairs are planned. " * 30)
        + "</p></article></main><script>" + ("secret " * 100) + "</script></html>"
    )
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response(html)):
        result = article_extractor.extract_article_text("https://example.com/story")
    assert result["success"] is True
    assert "Road funding" in result["text"]
    assert "secret" not in result["text"]
    assert "MENU" not in result["text"]


def test_rejects_private_url_before_network_request():
    with patch.object(article_extractor, "_validate_public_url", return_value=(False, "private_host")), \
         patch.object(article_extractor.requests, "get") as get:
        result = article_extractor.extract_article_text("http://127.0.0.1/admin")
    assert result["success"] is False
    assert result["status"] == "private_host"
    get.assert_not_called()


def test_rejects_non_html_response():
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response("data", content_type="application/pdf")):
        result = article_extractor.extract_article_text("https://example.com/file.pdf")
    assert result["success"] is False
    assert result["status"] == "not_html"


def test_rejects_short_generic_page():
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response("<html><body>Sign in</body></html>")):
        result = article_extractor.extract_article_text("https://example.com/story")
    assert result["success"] is False
    assert result["status"] == "extraction_failed"


def test_redirect_destination_is_revalidated():
    first = _response("", status=302, headers={"Location": "http://127.0.0.1/admin"})
    with patch.object(article_extractor, "_validate_public_url", side_effect=[(True, ""), (False, "private_host")]) as validate, \
         patch.object(article_extractor.requests, "get", return_value=first) as get:
        result = article_extractor.extract_article_text("https://example.com/story")
    assert result["success"] is False
    assert result["status"] == "private_host"
    assert validate.call_count == 2
    assert get.call_count == 1


def test_rejects_oversized_url():
    result = article_extractor.extract_article_text("https://example.com/" + "a" * 2100)
    assert result["success"] is False
    assert result["status"] == "invalid_url"
