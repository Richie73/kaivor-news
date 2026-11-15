"""FP090: one design system across all tabs.

The news page defines shared design tokens in :root (one palette, one set
of radii) and every main surface, border and text colour uses them instead
of hardcoded hex values. Card radii converge on the radius tokens, the
section title moves from an inline style into the stylesheet, and the
Reading page's tokens are aligned to the same values so both pages read
as one app.
"""

from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "index.html"
READING = Path(__file__).resolve().parent.parent / "templates" / "reading.html"


def _css(html):
    return html.split("<style>", 1)[1].split("</style>", 1)[0]


def test_root_tokens_defined():
    css = _css(TEMPLATE.read_text())
    for token in (
        "--bg:#0b0b0b",
        "--surface:#161618",
        "--surface-2:#1f1f23",
        "--surface-3:#2a2a2e",
        "--border:#26262a",
        "--border-strong:#2f2f36",
        "--border-input:#383842",
        "--line:#222",
        "--text:#f3f4f6",
        "--text-bright:#fff",
        "--text-2:#e5e7eb",
        "--text-3:#d1d5db",
        "--muted:#9ca3af",
        "--faint:#6b7280",
        "--brand:#35FA33",
        "--green:#10b981",
        "--green-bright:#34d399",
        "--green-soft:#a7f3d0",
        "--green-pale:#d1fae5",
        "--radius-sm:8px",
        "--radius-md:12px",
        "--radius-lg:16px",
        "--radius-pill:999px",
    ):
        assert token in css, token


def test_main_surfaces_use_tokens():
    css = _css(TEMPLATE.read_text())
    for rule in (
        "body { background:var(--bg); color:var(--text);",
        "header { position:fixed; top:0; left:0; right:0; background:var(--bg);",
        ".manager-card,.card { background:var(--surface); border-radius:var(--radius-md);",
        ".market-bar { display:block; overflow:hidden; padding:var(--space-md) 0; margin-bottom:var(--space-lg); font-size:var(--text-md); background:var(--surface);",
        ".weather-card { background:var(--surface); border:1px solid var(--border);",
        ".chip { flex: 0 0 auto; background:var(--surface-2); color:var(--muted);",
        ".market-panel { background:var(--green-panel); border:1px solid var(--green-border);",
        ".nav-item.active { color:var(--brand); }",
    ):
        assert rule in css, rule


def test_card_radii_converged():
    css = _css(TEMPLATE.read_text())
    for old_radius in (
        "border-radius:13px",
        "border-radius:14px",
        "border-radius:15px",
        "border-radius:16px",
        "border-radius:20px",
        "border-radius:10px",
        "border-radius:7px",
    ):
        assert old_radius not in css, old_radius


def test_section_title_is_a_stylesheet_rule():
    html = TEMPLATE.read_text()
    assert (
        "#section-title { font-size:var(--text-lg); color:var(--muted); "
        "text-transform:uppercase; letter-spacing:1px; margin-bottom:var(--space-xs); }"
        in html
    )
    assert '<h3 id="section-title">Top Stories</h3>' in html
    assert 'id="section-title" style=' not in html


def test_reading_tokens_match_news():
    css = _css(READING.read_text())
    for token in (
        "--bg:#0b0b0b",
        "--panel:#161618",
        "--panel2:#1f1f23",
        "--line:#26262a",
        "--muted:#9ca3af",
        "--text:#f3f4f6",
        "--accent:#10b981",
        "--brand:#35FA33",
        "--radius-sm:8px",
        "--radius-md:12px",
        "--radius-pill:999px",
    ):
        assert token in css, token


def test_reading_uses_shared_radii():
    css = _css(READING.read_text())
    assert "border-radius:var(--radius-md)" in css
    assert "border-radius:var(--radius-sm)" in css
    for old_radius in (
        "border-radius:15px",
        "border-radius:10px",
        "border-radius:9px",
        "border-radius:30px",
    ):
        assert old_radius not in css, old_radius


def test_bottom_nav_matches_across_pages():
    news_css = _css(TEMPLATE.read_text())
    reading_css = _css(READING.read_text())
    assert "background:var(--bg);border-top:1px solid var(--line)" in reading_css
    assert "#bottom-nav { position:fixed; left:0; right:0; bottom:0; z-index:1000; display:flex; background:var(--bg); border-top:1px solid var(--line);" in news_css
    assert ".nav-item.active{color:var(--brand)}" in reading_css
    assert ".nav-item.active { color:var(--brand); }" in news_css


def test_no_hardcoded_core_colours_in_main_rules():
    css = _css(TEMPLATE.read_text())
    for old_value in (
        "background:#161618",
        "background:#1f1f23",
        "color:#9ca3af",
        "color:#6b7280",
        "border:1px solid #26262a",
        "border:1px solid #2f2f36",
        "border:1px solid #383842",
        "color:#fff",
        "color:#f3f4f6",
        "color:#e5e7eb",
        "color:#d1d5db",
        "color:#10b981",
        "color:#35FA33",
        "color:#a7f3d0",
        "color:#d1fae5",
        "color:#f87171",
        "color:#fbbf24",
        "color:#7dd3fc",
    ):
        assert old_value not in css, old_value
