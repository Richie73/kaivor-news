"""FP083: logo refresh (Spark K) + splash screen.

The app icon is refreshed to the Spark K mark — a bold black K with
the Kaivor intelligence spark on the same green (#3aa76d) as the
current icon — shipped as v4 icon files (192 + 512), with the SVG
source kept in the repo. The manifest, service worker cache and
favicon all move to v4. The header on both pages shows the new mark.

The home page also gains a splash screen: the logo, wordmark and an
animated loading bar cover the first paint, then fade out once the
page is usable — with a hard 3s timeout so it can never trap the
user, and no animation when the user prefers reduced motion.

Icon sizes are read from the PNG headers directly (no Pillow
dependency — the phone suite must run without it).
"""
import json
import struct
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"
READING_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "reading.html"
MANIFEST = Path(__file__).resolve().parents[1] / "static" / "manifest.webmanifest"
SERVICE_WORKER = Path(__file__).resolve().parents[1] / "static" / "service-worker.js"
ICONS = Path(__file__).resolve().parents[1] / "static" / "icons"


def png_size(path):
    with open(path, "rb") as handle:
        header = handle.read(33)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def test_manifest_points_at_v4_icons():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    icons = {icon["sizes"]: icon for icon in manifest["icons"]}
    assert icons["192x192"]["src"] == "/icons/kaivor-news-192-v4.png"
    assert icons["192x192"]["purpose"] == "any"
    assert icons["512x512"]["src"] == "/icons/kaivor-news-512-v4.png"
    assert icons["512x512"]["purpose"] == "any maskable"
    assert "v2" not in MANIFEST.read_text(encoding="utf-8")
    assert "v3" not in MANIFEST.read_text(encoding="utf-8")


def test_v4_icon_files_exist_at_the_right_sizes():
    assert png_size(ICONS / "kaivor-news-192-v4.png") == (192, 192)
    assert png_size(ICONS / "kaivor-news-512-v4.png") == (512, 512)


def test_service_worker_caches_v4_icons():
    worker = SERVICE_WORKER.read_text(encoding="utf-8")
    # FP093 note: the cache name moved on (kaivor-news-fp093-offline-v1)
    # when offline reading arrived; the v4 icons are still cached.
    assert "kaivor-news-fp093-offline-v1" in worker
    assert "/icons/kaivor-news-192-v4.png" in worker
    assert "/icons/kaivor-news-512-v4.png" in worker
    assert "v2" not in worker
    assert "v3" not in worker


def test_favicon_points_at_v4():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert '<link rel="icon" href="/icons/kaivor-news-192-v4.png" type="image/png">' in html


def test_headers_show_the_logo():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert '<img class="brand-mark" src="/icons/kaivor-news-192-v4.png"' in html
    assert ".brand-mark {" in html
    reading = READING_TEMPLATE.read_text(encoding="utf-8")
    assert '<img class="brand-mark" src="/icons/kaivor-news-192-v4.png"' in reading
    assert ".brand-mark{" in reading


def test_splash_overlay_exists():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert '<div id="splash" aria-hidden="true">' in html
    assert 'class="splash-logo"' in html
    assert "M164 144 H208 V227 L352 144 V190 L236 257 L352 322 V368 L208 285 V368 H164 Z" in html
    assert '<div class="splash-word">KAIVOR</div>' in html
    assert '<div class="splash-tag">Your personal AI</div>' in html
    assert '<div class="splash-bar"><span></span></div>' in html
    assert "@keyframes splash-slide" in html
    assert "#splash.splash-hidden" in html


def test_splash_hides_on_load_with_a_safety_timeout():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "function hideSplash()" in html
    assert "setTimeout(hideSplash, 900)" in html
    assert "setTimeout(hideSplash, 400)" in html
    assert "setTimeout(hideSplash, 3000)" in html
    assert "splash.classList.add('splash-hidden')" in html
    assert "splash.style.display = 'none'" in html


def test_splash_respects_reduced_motion():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "#splash { transition:none; }" in html
    assert ".splash-logo, .splash-word, .splash-tag, .splash-bar, .splash-bar span, .splash-shine, .skeleton { animation:none; }" in html


def test_svg_source_is_in_the_repo():
    svg = (ICONS / "kaivor-logo-v4.svg").read_text(encoding="utf-8")
    assert 'fill="#3aa76d"' in svg
    assert "M164 144 H208 V227 L352 144 V190 L236 257 L352 322 V368 L208 285 V368 H164 Z" in svg
    assert "M404 152 L416 180 L444 192 L416 204 L404 232 L392 204 L364 192 L392 180 Z" in svg
