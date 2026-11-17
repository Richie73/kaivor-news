"""FP111.1: the header no longer hides the top of the page.

The header was position:fixed and ~107px tall (logo + tagline +
Settings button), but the body only cleared 70px — so the top
~37px of the page sat permanently under the header. The market
panel is the first element, so its "MARKET WATCH" heading was
sliced; FP111 exposed it by shrinking the panel's head row when
the refresh button moved out. The header is now position:sticky:
still pinned while scrolling, but taking its own space in the
layout, so no magic padding number is needed.
"""
import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_header_is_sticky_not_fixed():
    html = template_text()
    header = re.search(r"header \{([^}]*)\}", html)
    assert header, "header rule missing"
    assert "position:sticky" in header.group(1)
    assert "position:fixed" not in header.group(1)
    assert "top:0" in header.group(1)
    # Scrolled content must still slide UNDER the header, not over it.
    assert "z-index:1000" in header.group(1)
    assert "background:var(--bg)" in header.group(1)


def test_body_no_longer_clears_a_fixed_header():
    html = template_text()
    body = re.search(r"body \{([^}]*)\}", html)
    assert body, "body rule missing"
    assert "padding-top:70px" not in body.group(1)
    assert "padding-top:0" in body.group(1)
    # The bottom nav is still fixed, so its clearance stays.
    assert "padding-bottom:64px" in body.group(1)


def test_no_ancestor_breaks_sticky():
    # position:sticky fails when an ancestor between the header and
    # the viewport sets overflow (other than visible). The header is
    # a direct child of body, so only html/body rules can break it.
    html = template_text()
    style = re.search(r"<style>(.*?)</style>", html, re.S)
    assert style, "style block missing"
    assert not re.search(r"html \{[^}]*overflow", style.group(1))
    body = re.search(r"body \{([^}]*)\}", style.group(1))
    assert body, "body rule missing"
    assert "overflow" not in body.group(1)
