"""FP085: Settings gear + a more dynamic opening animation.

The "Sources & API Settings" block leaves the home page for a proper
Settings view behind a gear button in the header. It holds everything
settings-shaped in one place: adding a news source plus the list of
feeds Kaivor follows (with their working/broken status), the five API
keys, the personal relevance profile, and an About section with the
live story count and last refresh. The standalone Relevance view is
gone — it lives inside Settings now.

The splash screen also gets more life: a shine sweep crosses the logo
as the app opens, alongside the existing pop-in and loading bar.
"""
import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def show_settings_body():
    html = template_text()
    start = html.index("function showSettings(element){")
    end = html.index("async function loadSettingsFeeds(){", start)
    return html[start:end]


def test_settings_gear_is_in_the_header():
    html = template_text()
    assert '<button id="settings-btn" class="install-app" onclick="showSettings(this)">⚙️ Settings</button>' in html
    assert 'id="relevance-btn"' not in html
    header = html[html.index("<header>"):html.index("</header>")]
    assert "settings-btn" in header


def test_home_page_settings_block_is_gone():
    html = template_text()
    assert "Sources &amp; API Settings" not in html
    assert "manager-settings" not in html
    assert '<details class="manager-card' not in html


def test_settings_view_has_all_sections():
    body = show_settings_body()
    assert "News sources" in body
    assert 'id="feed-name"' in body
    assert 'id="feed-url"' in body
    assert "addCustomFeed()" in body
    assert 'id="settings-feeds-summary"' in body
    assert 'id="settings-feeds-list"' in body
    assert "API keys" in body
    for key_type in ("openrouter", "openai", "guardian", "brave", "newsdata"):
        assert f'id="{key_type}-key-input"' in body
        assert f"saveApiKey('{key_type}')" in body
    assert "Personal relevance" in body
    assert 'id="settings-relevance"' in body
    assert "About Kaivor" in body
    assert 'id="settings-about"' in body
    assert "unlock via the 📚 Reading tab" in body
    assert "loadSettingsFeeds();" in body
    assert "loadSettingsRelevance();" in body
    assert "loadSettingsAbout();" in body


def test_settings_loads_feeds_relevance_and_about():
    html = template_text()
    assert "async function loadSettingsFeeds(){" in html
    assert "fetch('/api/publisher-feeds'" in html
    assert "feed.publisher" in html
    assert "feed.article_count" in html
    assert "async function loadSettingsRelevance(){" in html
    assert "fetch('/api/relevance_profile'" in html
    assert "saveRelevanceProfile()" in html
    assert "async function loadSettingsAbout(){" in html
    assert "fetch('/api/health'" in html
    assert "news_last_updated" in html


def test_settings_view_hides_weather_and_opens_at_top():
    body = show_settings_body()
    assert "hideWeatherView();" in body
    assert "activateCategoryChip(element);" in body
    assert "scrollKaivorToTop();" in body
    assert "'Settings'" in body


def test_splash_has_the_shine_animation():
    html = template_text()
    assert 'class="splash-logo-wrap"' in html
    assert 'class="splash-shine"' in html
    assert "@keyframes splash-shine" in html
    assert ".splash-logo, .splash-word, .splash-tag, .splash-bar, .splash-bar span, .splash-shine { animation:none; }" in html
    assert 'class="splash-logo"' in html


def test_settings_deep_link():
    html = template_text()
    assert "else if (initialHash === '#settings') { showSettings(document.getElementById('settings-btn')); }" in html


def test_relevance_standalone_view_is_gone():
    html = template_text()
    assert "async function showRelevanceProfile(element){" not in html
    assert "function showRelevanceProfile" not in html
    assert "showRelevanceProfile(this)" not in html
    assert "async function saveRelevanceProfile()" in html
