"""FP084: bottom navigation bar + news-only category rail.

The fifteen-destination top rail is split: a fixed bottom bar holds
the six main destinations (Hub, News, Weather, Chat, Saved, Reading),
always visible and thumb-friendly, and the top rail keeps only the
ten news categories. Relevance moves to a button in the header.
Swiping moves between news categories only. The Reading page gets
the same bottom bar, linking back to the news page (with a hash
for the Hub, Weather, Chat and Saved views).
"""
import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"
READING_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "reading.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def rail_block(html):
    start = html.index('<div class="chips">')
    end = html.index("</div>", html.index("🧩 Puzzles", start)) + len("</div>")
    return html[start:end]


def nav_block(html):
    start = html.index('<nav id="bottom-nav"')
    end = html.index("</nav>", start) + len("</nav>")
    return html[start:end]


def test_bottom_nav_has_five_destinations():
    nav = nav_block(template_text())
    assert 'id="nav-hub"' in nav
    assert 'onclick="showMorningHub(this)"' in nav
    assert nav.index('id="nav-hub"') < nav.index('id="nav-news"')
    assert 'id="nav-news"' in nav
    assert 'onclick="filterCategory(\'All\', document.querySelector(\'.chips .chip\'))"' in nav
    assert 'id="nav-weather"' in nav
    assert 'onclick="showWeather(this)"' in nav
    assert 'id="nav-chat"' in nav
    assert 'onclick="showChat(this)"' in nav
    assert 'id="nav-saved"' in nav
    assert 'onclick="showSaved(this)"' in nav
    assert 'id="nav-reading"' in nav
    assert 'href="/reading"' in nav
    assert nav.count('class="nav-item') == 6
    assert 'data-nav="hub"' in nav
    assert 'data-nav="news"' in nav
    assert 'data-nav="weather"' in nav
    assert 'data-nav="chat"' in nav
    assert 'data-nav="saved"' in nav
    assert 'data-nav="reading"' in nav


def test_rail_holds_news_categories_only():
    rail = rail_block(template_text())
    chips = re.findall(r'<div class="chip[^>]*onclick="([^"]+)"', rail)
    assert len(chips) == 10, chips
    assert all(handler.startswith("filterCategory(") for handler in chips)
    assert "showWeather(" not in rail
    assert "showSaved(" not in rail
    assert "showRelevanceProfile(" not in rail
    assert "showChat(" not in rail
    assert "/reading" not in rail
    assert 'data-nav="news"' in rail


def test_relevance_lives_in_settings_not_the_header():
    # FP085: the header Relevance button is replaced by the Settings
    # gear; the relevance profile lives inside the Settings view.
    html = template_text()
    assert '<button id="settings-btn" class="install-app" onclick="showSettings(this)">⚙️ Settings</button>' in html
    assert 'id="relevance-btn"' not in html
    assert "showRelevanceProfile(this)" not in html
    assert "showRelevanceProfile(this)" not in rail_block(html)


def test_swipe_covers_news_categories_only():
    html = template_text()
    match = re.search(r"const swipeCategories = \(\) => Array\.from\(document\.querySelectorAll\((.*?)\)\);", html, re.S)
    assert match
    selector = match.group(1)
    assert 'filterCategory(' in selector
    assert 'showWeather(' not in selector
    assert 'showSaved(' not in selector
    assert 'showRelevanceProfile(' not in selector
    assert 'showChat(' not in selector
    assert 'data-scroll-to-end' not in selector


def test_nav_stays_in_step_with_activation():
    html = template_text()
    match = re.search(r"function activateCategoryChip\(element\) \{(.*?)\n\}", html, re.S)
    assert match
    body = match.group(1)
    assert "element.dataset.nav" in body
    assert "document.querySelectorAll('.nav-item')" in body
    assert "item.classList.toggle('active'" in body
    assert "if (!element.closest('.chips')) return;" in body
    assert "scrollCategoryChipIntoView(element)" in body


def test_deep_links_open_views_on_load():
    html = template_text()
    assert "window.location.hash" in html
    assert "if (initialHash === '#weather') { showWeather(document.getElementById('nav-weather')); }" in html
    assert "else if (initialHash === '#chat') { showChat(document.getElementById('nav-chat')); }" in html
    assert "else if (initialHash === '#saved') { showSaved(document.getElementById('nav-saved')); }" in html


def test_content_clears_the_bottom_bar():
    html = template_text()
    assert "padding-bottom:64px" in html
    nav_css = re.search(r"#bottom-nav \{(.*?)\}", html, re.S)
    assert nav_css
    assert "position:fixed" in nav_css.group(1).replace(" ", "")
    assert "env(safe-area-inset-bottom" in nav_css.group(1)
    assert ".nav-item.active { color:var(--brand); }" in html
    assert "bottom: calc(78px + env(safe-area-inset-bottom, 0px));" in html


def test_reading_page_has_the_bottom_bar():
    reading = READING_TEMPLATE.read_text(encoding="utf-8")
    nav = nav_block(reading)
    assert 'href="/"' in nav
    assert 'href="/#hub"' in nav
    assert 'href="/#weather"' in nav
    assert 'href="/#chat"' in nav
    assert 'href="/#saved"' in nav
    assert '<span class="nav-item active" data-nav="reading">' in nav
    assert "#bottom-nav{" in reading
    assert "padding:20px 14px 80px" in reading
