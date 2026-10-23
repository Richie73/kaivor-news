"""Static regression test for the pasted-text summary drawer visibility."""
from pathlib import Path
import re


def test_open_manual_text_brief_reveals_drawer_before_inserting_form():
    html = Path("templates/index.html").read_text(encoding="utf-8")
    match = re.search(
        r"function openManualTextBrief\(button\)\s*\{(?P<body>.*?)\n\}",
        html,
        re.S,
    )
    assert match, "openManualTextBrief function must exist"
    body = match.group("body")
    assert "setProperty('display', 'block', 'important')" in body
    assert body.index("setProperty('display', 'block', 'important')") < body.index("target.innerHTML =")
    assert "if (!card)" in body


def test_pasted_text_submit_does_not_inherit_article_publisher():
    html = Path("templates/index.html").read_text(encoding="utf-8")
    assert "CLICK HANDLER REACHED" not in html
    assert "source_type:'pasted_text'" in html
    assert "source:'User-supplied text'" in html
