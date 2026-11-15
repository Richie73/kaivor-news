"""FP088: loading states — skeleton screens while feeds and weather load.

1. NEWS: when the page loads with no stories (empty cache, e.g. right
   after a deploy), three skeleton cards + a note render instead of
   a blank feed, and a poll checks /api/health every 10s and reloads
   the page as soon as stories exist (30 attempts max, then the note
   says to reload by hand).
2. WEATHER: the strip and the full-view hero show skeleton shimmer
   while the forecast loads, instead of "Loading weather…" text.
3. MARKETS: the view opens with four skeleton rows instead of the
   "Loading market history…" line.
4. The shimmer is disabled under prefers-reduced-motion.
"""
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_skeleton_css_exists():
    html = template_text()
    assert ".skeleton { background:linear-gradient(90deg,var(--surface-2) 25%,var(--surface-3) 50%,var(--surface-2) 75%); background-size:200% 100%; animation:skeleton-shimmer 1.4s linear infinite; border-radius:var(--radius-sm); }" in html
    assert "@keyframes skeleton-shimmer { from { background-position:200% 0; } to { background-position:-200% 0; } }" in html
    assert ".skeleton-image { aspect-ratio:16/9; margin-bottom:8px; }" in html
    assert ".skeleton-row { height:44px; margin-bottom:8px; }" in html
    assert ".skeleton-inline { display:inline-block; width:90px; height:12px; margin-bottom:0; vertical-align:middle; }" in html


def test_news_skeleton_cards_render_when_empty():
    html = template_text()
    assert "{% if not articles %}" in html
    assert html.count('class="card skeleton-card"') == 3
    assert '<p id="skeleton-note" class="skeleton-note">Loading the latest stories…</p>' in html


def test_news_ready_poll_reloads_when_stories_exist():
    html = template_text()
    assert "(function pollNewsReady() {" in html
    assert "if (!document.querySelector('.skeleton-card')) return;" in html
    assert "const res = await fetch('/api/health', {cache:'no-store'});" in html
    assert "if (data.news_count > 0) { clearInterval(timer); location.reload(); return; }" in html
    assert "if (attempts >= 30) {" in html
    assert "Stories are taking a while — reload the page to try again." in html


def test_weather_shows_skeletons_while_loading():
    html = template_text()
    assert '<span id="weather-strip-now" class="weather-strip-now"><span class="skeleton skeleton-inline"></span></span>' in html
    assert '<div id="weather-now" class="weather-now"><div class="skeleton skeleton-hero"></div></div>' in html
    assert "if (nowEl) nowEl.innerHTML = '<div class=\"skeleton skeleton-hero\"></div>';" in html
    assert "if (stripNowEl) stripNowEl.innerHTML = '<span class=\"skeleton skeleton-inline\"></span>';" in html
    assert "Loading weather…" not in html
    assert "if (nowEl) nowEl.textContent = 'Weather unavailable — check your connection and try again.';" in html


def test_markets_view_opens_with_skeleton_rows():
    html = template_text()
    assert '<div id="markets-list"><div class="skeleton skeleton-row"></div><div class="skeleton skeleton-row"></div><div class="skeleton skeleton-row"></div><div class="skeleton skeleton-row"></div></div>' in html
    assert "Loading market history…" not in html


def test_skeletons_respect_reduced_motion():
    html = template_text()
    assert ".splash-logo, .splash-word, .splash-tag, .splash-bar, .splash-bar span, .splash-shine, .skeleton { animation:none; }" in html
