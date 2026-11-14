"""FP067c: final utility navigation items scroll the rail to its end.

SUPERSEDED by FP084: the utility destinations (Weather, Chat, Saved,
Reading) left the rail for a bottom navigation bar and Relevance moved
to a header button, so the scroll-to-end mechanism is gone. These tests
now assert the FP084 reality instead of the FP067c one.
"""
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def html():
    return TEMPLATE.read_text(encoding="utf-8")


def test_no_end_scroll_attributes_remain():
    source = html()
    assert 'data-scroll-to-end="true"' not in source
    assert "scrollToEnd" not in source


def test_end_scroll_helper_is_gone():
    source = html()
    assert "scrollCategoryRailToEnd" not in source
    assert "function scrollCategoryChipIntoView(element, behavior = 'smooth')" in source


def test_utility_destinations_live_in_the_bottom_nav():
    source = html()
    assert 'id="nav-weather"' in source
    assert 'id="nav-chat"' in source
    assert 'id="nav-saved"' in source
    assert 'id="nav-reading"' in source
    assert '<div class="chip" onclick="showSaved(this)">' not in source
    assert '<div class="chip" onclick="showChat(this)">' not in source


def test_relevance_lives_in_settings_not_the_rail_or_header():
    # FP085: the header Relevance button is replaced by the Settings
    # gear; the relevance profile lives inside the Settings view.
    source = html()
    assert 'id="settings-btn"' in source
    assert 'id="relevance-btn"' not in source
    assert '<div class="chip" onclick="showRelevanceProfile(this)">' not in source


def test_reduced_motion_is_respected_and_other_navigation_is_preserved():
    source = html()
    assert "prefers-reduced-motion: reduce" in source
    assert "function scrollCategoryChipIntoView(element, behavior = 'smooth')" in source
    assert "function animateCategoryTitle(title, direction)" in source
    assert "document.addEventListener('touchstart'" in source
    assert "document.addEventListener('touchend'" in source
