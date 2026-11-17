"""FP120: softer brand green.

Richie found the Spark K neon #35FA33 too bright, and picked
leaf green #3aa76d as the most polished of three softer
options. The swap covers every place the old green lived:
the tokens in both templates, the splash logo, the markets
sparkline, the market flash glow, the SVG logo source and the
PNG icons (rebuilt as v4 from the SVG geometry, so Android
picks the new icon up from the new URLs).

PNG sizes are read from the headers directly (no Pillow
dependency — the phone suite must run without it). The pixel
colours of the v4 icons were verified when they were built
(corner #3aa76d, K stem and spark black) and are recorded in
CHANGELOG_FP120.txt.
"""

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "templates" / "index.html"
READING = ROOT / "templates" / "reading.html"
SVG = ROOT / "static" / "icons" / "kaivor-logo-v4.svg"
MANIFEST = ROOT / "static" / "manifest.webmanifest"
WORKER = ROOT / "static" / "service-worker.js"
ICONS = ROOT / "static" / "icons"


def _png_size(path):
    with open(path, "rb") as handle:
        header = handle.read(33)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    return struct.unpack(">II", header[16:24])


def test_no_old_brand_green_left():
    for path in (INDEX, READING, SVG, MANIFEST, WORKER):
        text = path.read_text(encoding="utf-8").lower()
        assert "#35fa33" not in text, f"old green still in {path.name}"


def test_brand_tokens_are_leaf_green():
    index = INDEX.read_text(encoding="utf-8")
    for token in (
        "--brand:#3aa76d",
        "--green:#3aa76d",
        "--green-bright:#3aa76d",
        "--green-soft:#3aa76d",
        "--green-pale:#3aa76d",
        "--green-dark:#3aa76d",
    ):
        assert token in index, token
    reading = READING.read_text(encoding="utf-8")
    assert "--accent:#3aa76d" in reading
    assert "--brand:#3aa76d" in reading


def test_splash_sparkline_and_flash_use_leaf_green():
    html = INDEX.read_text(encoding="utf-8")
    assert 'fill="#3aa76d"' in html
    assert "up ? '#3aa76d'" in html
    assert "#3aa76d66" in html


def test_v4_icons_exist_and_v3_is_gone():
    assert _png_size(ICONS / "kaivor-news-192-v4.png") == (192, 192)
    assert _png_size(ICONS / "kaivor-news-512-v4.png") == (512, 512)
    assert not (ICONS / "kaivor-news-192-v3.png").exists()
    assert not (ICONS / "kaivor-news-512-v3.png").exists()
    assert not (ICONS / "kaivor-logo-v3.svg").exists()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    srcs = [icon["src"] for icon in manifest["icons"]]
    assert "/icons/kaivor-news-192-v4.png" in srcs
    assert "/icons/kaivor-news-512-v4.png" in srcs
    worker = WORKER.read_text(encoding="utf-8")
    assert "/icons/kaivor-news-192-v4.png" in worker
    assert "/icons/kaivor-news-512-v4.png" in worker
