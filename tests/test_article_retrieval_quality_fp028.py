"""FP028: article extraction quality and safe diagnostic regression tests."""
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


def test_prefers_semantic_article_and_reports_quality_metadata():
    article = (
        "<article class='article-body'><h1>Road funding changes</h1>"
        + "".join(f"<p>The transport department announced road funding changes for local authorities. Details include dates, costs and project plans. {i}.</p>" for i in range(12))
        + "</article>"
    )
    page = "<html><body><nav>" + ("Home Menu Search Sign in Subscribe " * 100) + "</nav>" + article + "</body></html>"
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response(page)):
        result = article_extractor.extract_article_text("https://example.com/story")
    assert result["success"] is True
    assert result["content_source"] == "semantic_container"
    assert result["quality_score"] >= 45
    assert "Road funding changes" in result["text"]
    assert "Home Menu Search" not in result["text"]


def test_rejects_long_cookie_and_subscription_boilerplate():
    boilerplate = " ".join([
        "Accept cookies to continue. Cookie preferences. Privacy policy. Terms of use.",
        "Sign in to continue. Subscribe now. Already a subscriber? Create a free account.",
        "Follow us on social media. Related articles. You may also like. Newsletter sign up.",
    ] * 18)
    page = "<html><body><div class='cookie-consent'>" + boilerplate + "</div><div>" + boilerplate + "</div></body></html>"
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response(page)):
        result = article_extractor.extract_article_text("https://example.com/story")
    assert result["success"] is False
    assert result["status"] == "extraction_failed"


def test_rejects_long_navigation_without_article_markup():
    nav = " ".join(f"Section {i} Home World Business Sport Technology Search Menu" for i in range(120))
    page = "<html><body><div class='site-menu'>" + nav + "</div></body></html>"
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response(page)):
        result = article_extractor.extract_article_text("https://example.com/story")
    assert result["success"] is False
    assert result["status"] == "extraction_failed"


def test_supports_publishers_without_semantic_article_markup_when_prose_is_good():
    paragraphs = "".join(
        f"<p>Officials said the new transport programme will improve local roads, repair damaged surfaces, and publish further project details next month. Update {i}.</p>"
        for i in range(10)
    )
    with patch.object(article_extractor, "_validate_public_url", return_value=(True, "")), \
         patch.object(article_extractor.requests, "get", return_value=_response("<html><body><div>" + paragraphs + "</div></body></html>")):
        result = article_extractor.extract_article_text("https://example.com/story")
    assert result["success"] is True
    assert result["quality_score"] >= 60
    assert result["content_source"] in {"semantic_container", "page_text_fallback"}
