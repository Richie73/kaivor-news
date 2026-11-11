"""FP067 regression checks for animated category title navigation."""
from pathlib import Path
import re

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_category_title_uses_direction_aware_animation():
    html = template_text()
    assert "function animateCategoryTitle(title, direction)" in html
    assert "const startX = direction === 'right' ? -28 : 28;" in html
    assert "titleElement.animate(" in html
    assert "duration: 230" in html


def test_category_title_animation_respects_reduced_motion():
    html = template_text()
    assert "prefers-reduced-motion: reduce" in html
    assert "typeof titleElement.animate !== 'function'" in html


def test_category_navigation_calculates_direction_from_chip_order():
    html = template_text()
    body = re.search(r"function filterCategory\(category, element\) \{(.*?)\n\}", html, re.S)
    assert body
    assert "previousIndex" in body.group(1)
    assert "nextIndex" in body.group(1)
    assert "nextIndex < previousIndex ? 'right' : 'left'" in body.group(1)


def test_category_title_updates_through_animation_helper():
    html = template_text()
    assert "animateCategoryTitle(category === 'All' ? 'Top Stories' : category + ' Stories', direction);" in html
    assert "titleElement.textContent = title;" in html


def test_fp066_swipe_navigation_is_preserved():
    html = template_text()
    assert "document.addEventListener('touchstart'" in html
    assert "document.addEventListener('touchend'" in html
    assert "Math.abs(deltaX) < 75" in html
    assert "filterCategory(match[1], nextChip)" in html


def test_fp066_scroll_to_top_is_preserved():
    html = template_text()
    assert 'id="kaivor-scroll-top"' in html
    assert "function scrollKaivorToTop" in html
    assert "if (wasDifferent) scrollKaivorToTop();" in html
