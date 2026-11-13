"""FP072: the category swipe activates the next destination with click().

Regression tests for the 13 Nov 2026 live failure: the FP067d swipe
dispatch parsed each chip's inline onclick with the regex
/filterCategory\\('([^']+)'\\)/, which never matched the real attributes
(filterCategory('All',this) carries a second argument), so swiping
between the ten filterCategory destinations silently did nothing. The
dispatch now activates the next chip with click(), reusing each chip's
own handler whatever its signature.
"""
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


def test_swipe_dispatch_uses_click_not_onclick_parsing():
    handler = swipe_handler()
    assert "chips[nextIndex].click()" in handler
    assert "getAttribute('onclick')" not in handler
    assert ".match(" not in handler
    assert "startsWith('filterCategory(')" not in handler


def test_buggy_filtercategory_regex_is_gone_from_template():
    html = source()
    assert r"/filterCategory\('([^']+)'\)/" not in html


def test_every_swipe_destination_is_click_activatable():
    """Each of the 13 swipe destinations must do the right thing when
    clicked: the ten category chips carry a filterCategory onclick, Saved
    and Relevance carry their own onclick, and Reading is a link."""
    html = source()
    category_chips = re.findall(
        r'<div class="chip[^"]*" onclick="filterCategory\(\'([^\']+)\',this\)">',
        html,
    )
    assert len(category_chips) == 10, category_chips
    assert 'onclick="showSaved(this)"' in html
    assert 'onclick="showRelevanceProfile(this)"' in html
    assert re.search(r'<a class="chip"[^>]*href="/reading"', html)


def test_swipe_still_moves_to_adjacent_destination():
    handler = swipe_handler()
    assert "currentIndex + (deltaX < 0 ? 1 : -1)" in handler
    assert "nextIndex !== currentIndex" in handler
    assert "Math.max(0, Math.min(chips.length - 1," in handler


def test_swipe_guards_unchanged():
    handler = swipe_handler()
    assert "Math.abs(deltaX) < 75" in handler
    assert "Math.abs(deltaX) < Math.abs(deltaY) * 1.25" in handler
    assert "touchStartTarget.closest('.card a, .btn-group, .evidence-details')" in handler
