"""FP067d: horizontal swipes traverse all category and utility destinations."""
from pathlib import Path
import re

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def source():
    return TEMPLATE.read_text(encoding="utf-8")


def swipe_handler():
    html = source()
    match = re.search(
        r"document\.addEventListener\('touchend', event => \{(.*?)\n    \}, \{ passive: true \}\);",
        html,
        re.S,
    )
    assert match
    return match.group(1)


def test_swipe_sequence_includes_categories_saved_relevance_and_reading():
    html = source()
    match = re.search(r"const swipeCategories = \(\) => Array\.from\(document\.querySelectorAll\((.*?)\)\);", html, re.S)
    assert match
    selector = match.group(1)
    assert 'filterCategory(' in selector
    assert 'showSaved(' in selector
    assert 'showRelevanceProfile(' in selector
    assert 'a[data-scroll-to-end="true"]' in selector


def test_swipe_dispatches_each_navigation_type():
    handler = swipe_handler()
    assert "action.startsWith('filterCategory(')" in handler
    assert "filterCategory(match[1], nextChip)" in handler
    assert "action.startsWith('showSaved(')" in handler
    assert "showSaved(nextChip)" in handler
    assert "action.startsWith('showRelevanceProfile(')" in handler
    assert "showRelevanceProfile(nextChip)" in handler
    assert "nextChip.matches('a[href]')" in handler
    assert "nextChip.click()" in handler


def test_reading_swipe_reuses_fp067c_end_scroll_click_handler():
    html = source()
    assert "document.addEventListener('click'" in html
    assert "scrollCategoryRailToEnd(link)" in html
    assert "window.location.assign(destination)" in html


def test_swipe_threshold_and_vertical_gesture_protection_remain():
    handler = swipe_handler()
    assert "Math.abs(deltaX) < 75" in handler
    assert "Math.abs(deltaX) < Math.abs(deltaY) * 1.25" in handler


def test_fp067a_to_fp067c_navigation_behaviour_is_preserved():
    html = source()
    assert "function activateCategoryChip(element)" in html
    assert "scrollCategoryChipIntoView(element)" in html
    assert "scrollCategoryRailToEnd(element)" in html
    assert "function animateCategoryTitle(title, direction)" in html
