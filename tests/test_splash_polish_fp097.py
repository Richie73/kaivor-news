"""FP097: the splash lets its own animation finish.

The splash already faded out smoothly (FP083), but it hid 900ms
after the page parsed — before the shine sweep (1.4s + 0.45s
delay = 1.85s) had finished, so the animation was cut off
mid-sweep. hideSplash now waits for a 2s minimum display: an
early call reschedules itself for the remaining time instead of
hiding, and only one reschedule is ever queued. The hard 3s
timeout still caps the splash on a slow load.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

NODE_PREAMBLE = """
let now = 1000;
const timeouts = [];
const splash = { dataset: {}, classList: { added: null, add(c) { this.added = c; } }, style: {} };
const document = { getElementById: () => splash, addEventListener: () => {} };
const window = { setTimeout: (fn, ms) => { timeouts.push({fn, ms}); return timeouts.length; }, addEventListener: () => {} };
const Date = { now: () => now };
"""

NODE_ASSERTIONS = """
// The hard 3s timeout is scheduled at load (timeouts[0]).
assert.equal(timeouts.length, 1);
assert.equal(timeouts[0].ms, 3000);
hideSplash();
assert.equal(splash.classList.added, null);
assert.equal(timeouts.length, 2);
assert.equal(timeouts[1].ms, 2000);
hideSplash();
assert.equal(timeouts.length, 2);
now = 1900;
hideSplash();
assert.equal(splash.classList.added, null);
assert.equal(timeouts.length, 2);
now = 3000;
hideSplash();
assert.equal(splash.classList.added, 'splash-hidden');
assert.equal(splash.dataset.hidden, 'true');
assert.equal(timeouts.length, 3);
assert.equal(timeouts[2].ms, 500);
"""


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_splash_minimum_display():
    html = template_text()
    assert "const SPLASH_MIN_MS = 2000;" in html
    assert "const splashStart = Date.now();" in html
    assert "const remaining = SPLASH_MIN_MS - (Date.now() - splashStart);" in html
    assert "window.setTimeout(hideSplash, remaining);" in html
    assert "setTimeout(hideSplash, 3000)" in html


def test_splash_fade_unchanged():
    html = template_text()
    assert "#splash.splash-hidden { opacity:0; pointer-events:none; }" in html
    assert "splash.classList.add('splash-hidden');" in html
    assert "window.setTimeout(() => { splash.style.display = 'none'; }, 500);" in html


def test_splash_timing_runs_under_node():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    html = template_text()
    match = re.search(
        r"const splashStart = Date\.now\(\);(.*?)// FP083 SPLASH: END",
        html,
        re.S,
    )
    assert match, "splash block missing"
    js = match.group(0).replace("// FP083 SPLASH: END", "")
    script = (
        "import assert from 'node:assert/strict';\n"
        + NODE_PREAMBLE
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
