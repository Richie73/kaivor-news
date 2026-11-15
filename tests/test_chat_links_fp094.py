"""FP094: links in chat replies are tappable.

renderAiMarkdown had no link support, so a web address the model
gave in a chat reply (or an AI brief) showed as plain text.
Markdown links [text](url) and bare https:// URLs now render as
anchors opening in a new tab. Only http(s) links: a javascript:
URL stays plain text, and code spans are never linked.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

# escapeHtml builds a div in the browser; the node stub below mimics
# the escaping a text node gets when serialised (&, <, >).
NODE_PREAMBLE = """
const document = { createElement: () => { let raw = ''; return {
    set textContent(v) { raw = String(v ?? ''); },
    get innerHTML() { return raw.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
}; } };
"""

NODE_ASSERTIONS = """
assert.equal(
    renderAiMarkdown('Read the [BBC report](https://www.bbc.co.uk/news) today.'),
    '<p>Read the <a href="https://www.bbc.co.uk/news" target="_blank" rel="noopener noreferrer">BBC report</a> today.</p>'
);
assert.equal(
    renderAiMarkdown('See https://example.com/foo for details.'),
    '<p>See <a href="https://example.com/foo" target="_blank" rel="noopener noreferrer">https://example.com/foo</a> for details.</p>'
);
assert.equal(
    renderAiMarkdown('It is at https://example.com/foo.'),
    '<p>It is at <a href="https://example.com/foo" target="_blank" rel="noopener noreferrer">https://example.com/foo</a>.</p>'
);
assert.ok(!renderAiMarkdown('[click](javascript:alert(1))').includes('<a '));
assert.ok(!renderAiMarkdown('`https://example.com/foo`').includes('<a '));
assert.ok(renderAiMarkdown('`https://example.com/foo`').includes('<code>https://example.com/foo</code>'));
assert.equal(
    renderAiMarkdown('**Bold** and [a link](https://example.com).'),
    '<p><strong>Bold</strong> and <a href="https://example.com" target="_blank" rel="noopener noreferrer">a link</a>.</p>'
);
assert.equal(
    renderAiMarkdown('Source: https://example.com/a?x=1&y=2'),
    '<p>Source: <a href="https://example.com/a?x=1&amp;y=2" target="_blank" rel="noopener noreferrer">https://example.com/a?x=1&amp;y=2</a></p>'
);
"""


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_markdown_link_replace_present():
    html = template_text()
    assert "'<a href=\"$2\" target=\"_blank\" rel=\"noopener noreferrer\">$1</a>'" in html


def test_bare_url_replace_present():
    html = template_text()
    assert "(^|[\\s(])(https?:\\/\\/[^\\s<]+)" in html
    assert "url.replace(/[.,;:!?)]+$/, '')" in html


def test_chat_link_rendering_runs_under_node():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    html = template_text()
    match = re.search(
        r"function renderAiMarkdown\(text\)\{(.*?)\n\}",
        html,
        re.S,
    )
    assert match, "renderAiMarkdown function missing"
    js = match.group(0)
    escape = re.search(
        r"function escapeHtml\(value\) \{[^\n]*\}",
        html,
    )
    assert escape, "escapeHtml function missing"
    script = (
        "import assert from 'node:assert/strict';\n"
        + NODE_PREAMBLE
        + escape.group(0)
        + "\n"
        + js
        + NODE_ASSERTIONS
    )
    with tempfile.NamedTemporaryFile(
        "w", suffix=".mjs", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(script)
        path = handle.name
    result = subprocess.run(
        [node, path], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
