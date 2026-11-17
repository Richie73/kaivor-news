"""FP117: one green across the whole app.

Every accent green is the Spark K brand green #35FA33 — the
logo's green. Dark surfaces and muted text are tints of that
same hue (120 degrees: red == blue, green dominant), so
nothing clashes and nothing is unreadable — pure neon on every
background would have been. The old emerald/teal greens
(#10b981, #34d399, #22c55e, #a7f3d0 and the rest) are gone.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "templates" / "index.html"
READING = ROOT / "templates" / "reading.html"

BRAND = "#35FA33"

# Every green allowed anywhere in either template: the brand
# itself, the brand with alpha (the market flash glow), the
# dark-on-brand text colour, and the hue-120 tints.
ALLOWED_GREENS = {
    "#35fa33",
    "#35fa3366",
    "#071207",
    "#0f1a0f",
    "#1f3d1f",
    "#1c2b1c",
    "#264026",
    "#0f2a0f",
    "#1a4d1a",
    "#111a11",
    "#0f150f",
    "#d6e8d6",
    "#8a9a8a",
    "#c2d2c2",
    "#eaf6ea",
    "#a8bfa8",
    "#9db29d",
    "#b3c6b3",
}

OLD_GREENS = (
    "#10b981", "#22c55e", "#34d399", "#a7f3d0", "#d1fae5",
    "#059669", "#064e3b", "#6ee7b7", "#86efac", "#14532d",
    "#123126", "#111816", "#0f1513", "#d7eee5", "#20362e",
    "#71847c", "#c9d8d2", "#e4fff3", "#a9beb6", "#1e3029",
    "#70827b", "#9ab5aa", "#10231c", "#1f4d3b", "#b7c8c0",
    "#20342c", "#7f918a", "#06130e", "#06251b", "#101512",
    "#214537", "#1f2f2a", "#2a473b", "#10b98166",
)

HEX_RE = re.compile(r"#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?\b")


def _is_greenish(rgb):
    r, g, b = (int(rgb[i:i + 2], 16) for i in (0, 2, 4))
    return g > r and g > b


def test_accent_green_tokens_are_the_brand_green():
    css = INDEX.read_text(encoding="utf-8")
    for token in (
        "--green:#35FA33",
        "--green-bright:#35FA33",
        "--green-soft:#35FA33",
        "--green-pale:#35FA33",
        "--green-dark:#35FA33",
    ):
        assert token in css, token


def test_dark_tints_come_from_the_brand_hue():
    css = INDEX.read_text(encoding="utf-8")
    for token in (
        "--green-panel:#0f1a0f",
        "--green-border:#1f3d1f",
        "--btn-bg:#1c2b1c",
        "--btn-border:#264026",
        "--green-darker:#0f2a0f",
        "--on-brand:#071207",
    ):
        assert token in css, token


def test_reading_accent_is_the_brand_green():
    css = READING.read_text(encoding="utf-8")
    assert "--accent:#35FA33" in css
    assert "--on-brand:#071207" in css
    assert "button.primary{background:var(--accent);color:var(--on-brand)" in css


def test_no_old_green_anywhere():
    for path in (INDEX, READING):
        text = path.read_text(encoding="utf-8").lower()
        for old in OLD_GREENS:
            assert old not in text, f"{old} still in {path.name}"


def test_every_green_in_either_template_is_allowed():
    for path in (INDEX, READING):
        text = path.read_text(encoding="utf-8")
        for match in HEX_RE.finditer(text):
            full = "#" + match.group(0)[1:].lower()
            rgb = match.group(1)
            if _is_greenish(rgb):
                assert full in ALLOWED_GREENS, f"{full} in {path.name} is not the one green"


def test_bright_buttons_use_dark_text():
    css = INDEX.read_text(encoding="utf-8")
    assert ".btn-save { background:var(--green-dark); color:var(--on-brand); border:none; }" in css
    assert "background: var(--green);\n            color: var(--on-brand);" in css


def test_price_up_uses_brand_and_panel_tokens():
    css = INDEX.read_text(encoding="utf-8")
    assert ".market-value.price-up { color:var(--brand); background:var(--green-panel); }" in css
