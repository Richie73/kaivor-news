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


def test_swipe_sequence_covers_news_categories_only():
    # FP084: the utility destinations left the rail for the bottom nav,
    # so swiping moves between the news categories only.
    html = source()
    match = re.search(r"const swipeCategories = \(\) => Array\.from\(document\.querySelectorAll\((.*?)\)\);", html, re.S)
    assert match
    selector = match.group(1)
    assert 'filterCategory(' in selector
    assert 'showWeather(' not in selector
    assert 'showSaved(' not in selector
    assert 'showRelevanceProfile(' not in selector
    assert 'showChat(' not in selector
    assert 'a[data-scroll-to-end="true"]' not in selector


def test_swipe_dispatches_each_navigation_type():
    handler = swipe_handler()
    # FP072: the dispatch no longer parses inline onclick attributes — the
    # FP067d regex (/filterCategory\('([^']+)'\)/) never matched the real
    # attributes (filterCategory('All',this) has a second argument), so
    # swiping between categories silently did nothing. Every destination
    # is now activated the same way a tap activates it.
    assert ".click()" in handler
    assert "getAttribute('onclick')" not in handler
    assert "filterCategory(match[1]" not in handler
    assert "showSaved(nextChip)" not in handler
    assert "showRelevanceProfile(nextChip)" not in handler


def test_reading_is_a_bottom_nav_link_not_a_rail_end_action():
    # FP084: Reading left the rail, so the click handler that waited
    # for the rail to scroll before following the link is gone.
    html = source()
    assert 'id="nav-reading"' in html
    assert 'href="/reading"' in html
    assert "scrollCategoryRailToEnd" not in html
    assert "window.location.assign(destination)" not in html


def test_swipe_threshold_and_vertical_gesture_protection_remain():
    handler = swipe_handler()
    assert "Math.abs(deltaX) < 75" in handler
    assert "Math.abs(deltaX) < Math.abs(deltaY) * 1.25" in handler


def test_fp067a_to_fp067c_navigation_behaviour_is_preserved():
    # FP084: the end-scroll helper is gone with the rail's utility
    # destinations; the shared activation and chip-centring remain.
    html = source()
    assert "function activateCategoryChip(element)" in html
    assert "scrollCategoryChipIntoView(element)" in html
    assert "scrollCategoryRailToEnd(element)" not in html
    assert "function animateCategoryTitle(title, direction)" in html
