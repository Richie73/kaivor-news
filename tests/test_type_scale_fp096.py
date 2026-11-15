"""FP096: type scale + spacing tidy-up (design system, part 2).

FP090 unified colours and corner radii; text sizes and spacing
were still mixed — 15 distinct font sizes and 7 line-heights in
the news page alone. The stylesheet now uses type tokens
(8 steps), leading tokens (4) and spacing tokens (4/8/12/16).
Convergences: 9px badges -> 10px, 15/17px headings -> 16px,
1.38/1.45 line-heights -> 1.4/1.5, 1.65 -> 1.6. Deliberately left
hardcoded: the icon glyph sizes (18/22/44px) and a few off-scale
margins (6/9/11px). The article description's styling also moves
out of its inline style (duplicated in both card renders) into
one rule.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "templates" / "index.html"
READING = ROOT / "templates" / "reading.html"


def style_block(path):
    text = path.read_text(encoding="utf-8")
    start = text.index("<style>")
    end = text.index("</style>")
    return text[start:end]


def test_text_tokens_defined():
    css = style_block(INDEX)
    for token, value in [
        ("--text-xs", "10px"),
        ("--text-sm", "11px"),
        ("--text-base", "12px"),
        ("--text-md", "13px"),
        ("--text-lg", "14px"),
        ("--text-xl", "16px"),
        ("--text-2xl", "20px"),
        ("--text-hero", "48px"),
    ]:
        assert f"{token}:{value}" in css, f"{token} missing"


def test_leading_and_space_tokens_defined():
    css = style_block(INDEX)
    for token, value in [
        ("--leading-none", "1"),
        ("--leading-snug", "1.4"),
        ("--leading-normal", "1.5"),
        ("--leading-relaxed", "1.6"),
        ("--space-xs", "4px"),
        ("--space-sm", "8px"),
        ("--space-md", "12px"),
        ("--space-lg", "16px"),
    ]:
        assert f"{token}:{value}" in css, f"{token} missing"


def test_no_hardcoded_on_scale_font_sizes():
    css = style_block(INDEX)
    assert not re.search(r"font-size:\s*(9|10|11|12|13|14|15|16|17|20|48)px", css)
    assert "1.02rem" not in css
    # Icon glyph sizes stay hardcoded by design.
    assert "font-size:18px" in css
    assert "font-size:44px" in css


def test_no_hardcoded_on_scale_leading_margins_or_gaps():
    css = style_block(INDEX)
    assert "line-height:1" not in css
    assert not re.search(r"margin-bottom:(4|8|12|16)px", css)
    assert not re.search(r"margin-top:(4|8|12|16)px", css)
    assert not re.search(r"gap:(4|8|12)px", css)


def test_article_description_rule_replaces_inline_styles():
    html = INDEX.read_text(encoding="utf-8")
    assert (
        ".article-description { font-size:var(--text-md); color:var(--muted); "
        "line-height:var(--leading-snug); margin-bottom:var(--space-md); }"
        in html
    )
    assert 'class="article-description" style=' not in html
    assert html.count('class="article-description"') == 2


def test_reading_page_uses_same_tokens():
    css = style_block(READING)
    for token in ["--text-xs", "--text-sm", "--text-base", "--text-md",
                  "--text-lg", "--text-xl", "--text-2xl", "--text-display",
                  "--leading-none", "--space-xs", "--space-md"]:
        assert token in css, f"{token} missing from reading.html"
    assert not re.search(r"font-size:(11|12|13|16|17|20|25|26)px", css)
    assert "font-size:var(--text-display)" in css
