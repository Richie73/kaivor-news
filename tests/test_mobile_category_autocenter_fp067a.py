"""FP067a regression checks updated for the shared FP067b rail helper."""
from pathlib import Path
import re

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def helper_body(html):
    match = re.search(
        r"function scrollCategoryChipIntoView\(element, behavior = 'smooth'\) \{(.*?)\n\}",
        html,
        re.S,
    )
    assert match, "shared category-rail scrolling helper is missing"
    return match.group(1)


def test_active_category_is_auto_centered_in_its_horizontal_rail():
    html = template_text()
    body = re.search(r"function activateCategoryChip\(element\) \{(.*?)\n\}", html, re.S)
    assert body
    assert "scrollCategoryChipIntoView(element)" in body.group(1)
    code = helper_body(html)
    assert "element.closest('.chips')" in code
    assert "getBoundingClientRect()" in code
    assert "chipCenter - (rail.clientWidth / 2)" in code
    assert "rail.scrollTo({ left: targetLeft" in code


def test_category_auto_centering_respects_reduced_motion():
    code = helper_body(template_text())
    assert "prefers-reduced-motion: reduce" in code
    assert "reducedMotion ? 'auto' : behavior" in code


def test_auto_centering_scrolls_only_the_category_rail():
    code = helper_body(template_text())
    assert "rail.scrollTo({ left: targetLeft" in code
    assert "rail.scrollLeft = targetLeft" in code
    assert "window.scrollTo(" not in code


def test_fp067_title_animation_is_preserved():
    html = template_text()
    assert "function animateCategoryTitle(title, direction)" in html
    assert "titleElement.animate(" in html


def test_fp066_swipe_navigation_and_scroll_to_top_are_preserved():
    html = template_text()
    assert "document.addEventListener('touchstart'" in html
    assert "document.addEventListener('touchend'" in html
    assert "Math.abs(deltaX) < 75" in html
    assert 'id="kaivor-scroll-top"' in html
    assert "if (wasDifferent) scrollKaivorToTop();" in html
