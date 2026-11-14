"""FP067b regression checks for complete horizontal category-rail navigation."""
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
    assert match
    return match.group(1)


def test_rail_scroll_uses_visible_geometry_and_true_maximum():
    code = helper_body(template_text())
    assert "getBoundingClientRect()" in code
    assert "rail.scrollWidth - rail.clientWidth" in code
    assert "Math.min(" in code and "Math.max(0" in code
    assert "rail.scrollTo({ left: targetLeft" in code


def test_rail_has_no_end_actions_reading_lives_in_the_bottom_nav():
    # FP084: the utility destinations left the rail, so the
    # scroll-to-end mechanism is gone — Reading is a bottom-nav link.
    html = template_text()
    assert 'data-scroll-to-end="true"' not in html
    assert "scrollCategoryRailToEnd" not in html
    assert 'href="/reading"' in html
    assert 'id="nav-reading"' in html


def test_rail_has_end_padding_and_items_do_not_shrink():
    html = template_text()
    chips_css = re.search(r"\.chips \{(.*?)\n        \}", html, re.S)
    chip_css = re.search(r"\.chip \{(.*?)\}", html, re.S)
    assert chips_css and "padding: 10px 24px 10px 12px" in chips_css.group(1)
    assert "scroll-padding-inline: 12px" in chips_css.group(1)
    assert chip_css and "flex: 0 0 auto" in chip_css.group(1)


def test_reduced_motion_is_respected():
    code = helper_body(template_text())
    assert "prefers-reduced-motion: reduce" in code
    assert "reducedMotion ? 'auto' : behavior" in code


def test_category_activation_uses_shared_scroll_helper():
    html = template_text()
    body = re.search(r"function activateCategoryChip\(element\) \{(.*?)\n\}", html, re.S)
    assert body
    assert "scrollCategoryChipIntoView(element)" in body.group(1)


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
