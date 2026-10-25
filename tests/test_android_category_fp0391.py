"""FP039.1 regression: Android remains enabled after later category additions."""
from pathlib import Path


def test_refresh_pipeline_includes_android_category():
    source = Path("main.py").read_text(encoding="utf-8")
    assert 'for category in ("World", "Technology", "Android", "Culture", "Business", "Science", "UK", "Sport"):' in source


def test_android_category_has_feed_registry_and_ui_filter():
    freshness = Path("news_freshness.py").read_text(encoding="utf-8")
    template = Path("templates/index.html").read_text(encoding="utf-8")
    assert '"Android": [' in freshness
    assert "filterCategory('Android',this)" in template
