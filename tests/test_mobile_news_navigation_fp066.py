"""FP066 regression checks for mobile news navigation behaviour."""

from pathlib import Path
import re

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_scroll_to_top_control_is_accessible_and_present():
    html = template_text()
    assert 'id="kaivor-scroll-top"' in html
    assert 'aria-label="Scroll to top"' in html
    assert "function scrollKaivorToTop" in html
    assert "window.scrollTo({ top: 0, left: 0, behavior })" in html


def test_scroll_button_only_appears_after_meaningful_scroll():
    html = template_text()
    assert "window.scrollY > 420" in html
    assert "#kaivor-scroll-top.is-visible" in html
    assert "topButton.addEventListener('click'" in html


def test_category_switch_resets_scroll_only_when_category_changes():
    html = template_text()
    body = re.search(r"function filterCategory\(category, element\) \{(.*?)\n\}", html, re.S)
    assert body
    assert "const wasDifferent = !element.classList.contains('active');" in body.group(1)
    assert "if (wasDifferent) scrollKaivorToTop();" in body.group(1)


def test_swipe_navigation_uses_category_chips_and_horizontal_threshold():
    html = template_text()
    assert "document.addEventListener('touchstart'" in html
    assert "document.addEventListener('touchend'" in html
    assert "Math.abs(deltaX) < 75" in html
    assert "Math.abs(deltaX) < Math.abs(deltaY) * 1.25" in html
    assert "'.chip[onclick^=\"filterCategory(\"]'" in html
    # FP072: the swipe activates the next chip with click() instead of
    # parsing its inline onclick (the FP067d regex never matched the
    # real filterCategory('X',this) attributes).
    assert "chips[nextIndex].click()" in html


def test_swipe_ignores_interactive_controls_and_chip_scroller():
    html = template_text()
    assert "input, textarea, select, button, a, [contenteditable=\"true\"], .chips" in html
    assert "touchcancel" in html


def test_navigation_initializes_after_dom_ready():
    html = template_text()
    assert "initializeMobileNewsNavigation();" in html
    assert "document.addEventListener('DOMContentLoaded'" in html


def test_saved_and_relevance_views_also_open_at_top():
    html = template_text()
    for name in ("showSaved", "showRelevanceProfile"):
        start = html.find(f"async function {name}")
        assert start >= 0
        function_head = html[start:start + 350]
        assert "scrollKaivorToTop()" in function_head
