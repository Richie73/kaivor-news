"""FP085.1: tapping a news category (or News in the bottom bar) after
opening Saved, Chat or Settings brings the stories back.

Those three views replace the news cards in #articles-container, so
filterCategory used to find only the view's cards: tapping News left
the view in place, and tapping a single category left the list blank.
The fix caches the news HTML before a view replaces it and restores
it when a news category is picked. The flag stops one view caching
another view as "news" (the Saved view's cards look like news cards),
and the restore re-syncs each card's Save button from savedIds in
case a story was unsaved while the Saved view was open.
"""
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def function_body(html, opener, next_opener):
    start = html.index(opener)
    end = html.index(next_opener, start)
    return html[start:end]


def test_news_cache_helpers_exist():
    html = template_text()
    assert "let cachedNewsHtml = null;" in html
    assert "let newsViewReplaced = false;" in html
    assert "function cacheNewsContainer() {" in html
    assert "function restoreNewsContainer() {" in html


def test_filter_category_restores_news_first():
    html = template_text()
    body = function_body(html, "function filterCategory(category, element) {",
                         "function initializeMobileNewsNavigation() {")
    restore_at = body.index("restoreNewsContainer();")
    cards_at = body.index("const cards = Array.from(container.querySelectorAll('.card'));")
    assert restore_at < cards_at


def test_views_cache_news_before_replacing():
    html = template_text()
    cases = [
        ("async function showSaved(element) {", "function loadChatHistory() {"),
        ("function showChat(element) {", "function saveChatWebToggle() {"),
        ("function showSettings(element){", "async function loadSettingsFeeds(){"),
    ]
    for opener, next_opener in cases:
        body = function_body(html, opener, next_opener)
        cache_at = body.index("cacheNewsContainer();")
        replace_at = body.index("container.innerHTML")
        assert cache_at < replace_at, opener


def test_cache_only_taken_from_the_news_view():
    html = template_text()
    body = function_body(html, "function cacheNewsContainer() {",
                         "function restoreNewsContainer() {")
    assert "if (newsViewReplaced) return;" in body
    assert "cachedNewsHtml = container.innerHTML;" in body
    assert "newsViewReplaced = true;" in body
    restore_body = function_body(html, "function restoreNewsContainer() {",
                                 "function initializeMobileNewsNavigation() {")
    assert "if (!newsViewReplaced) return true;" in restore_body
    assert "container.innerHTML = cachedNewsHtml;" in restore_body
    assert "newsViewReplaced = false;" in restore_body


def test_restore_resyncs_save_buttons():
    html = template_text()
    body = function_body(html, "function restoreNewsContainer() {",
                         "function initializeMobileNewsNavigation() {")
    assert "savedIds.has(card.dataset.articleId)" in body
    assert "button.textContent = 'Saved ✓'" in body
    assert "button.textContent = 'Save'" in body
