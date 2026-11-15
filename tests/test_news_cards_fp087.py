"""FP087: news cards — consistent image crops, source labels, clean timestamps.

1. Every card image is the same 16:9 shape (aspect-ratio + object-fit:
   cover), instead of natural height capped at 220px.
2. The category tag, provider badge and source name sit on one
   .card-source row in BOTH card renders (the Jinja loop and the
   Saved view's JS render), instead of the source name dropping
   onto its own line.
3. The timestamp's inline style moves into a .published stylesheet
   rule in both renders. The class name stays .published —
   formatArticleDates and articleFromCard both depend on it.
"""
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_card_images_have_a_fixed_crop():
    html = template_text()
    rule = ".card-image { width:100%; aspect-ratio:16/9; object-fit:cover; border-radius:var(--radius-sm); margin:0 0 8px; display:block; background:var(--surface-2); }"
    assert rule in html
    assert "max-height:220px" not in html


def test_card_source_row_style():
    html = template_text()
    assert ".card-source { display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; margin-bottom:8px; }" in html
    assert ".card-source .source-name { margin-bottom:0; }" in html


def test_both_card_renders_use_the_source_row():
    html = template_text()
    # Jinja render (news list).
    assert '<div class="card-source"><span class="source-tag">{{ article.category }}</span>' in html
    assert '<div class="source-name">{{ article.source }}</div></div>' in html
    # Saved view JS render.
    assert '<div class="card-source"><span class="source-tag">${escapeHtml(article.category)}</span>' in html
    assert '<div class="source-name">${escapeHtml(article.source)}</div></div>' in html


def test_published_style_lives_in_the_stylesheet():
    html = template_text()
    assert ".published { font-size:11px; color:var(--faint); margin-bottom:8px; }" in html
    assert '<div class="published">{{ article.published | display_date }}</div>' in html
    assert '<div class="published" data-published="${escapeHtml(article.published)}">${escapeHtml(formatDisplayDate(article.published))}</div>' in html
    assert 'class="published" style=' not in html


def test_published_class_name_kept_for_the_date_rewriter():
    html = template_text()
    assert "root.querySelectorAll('.published')" in html
    assert "card.querySelector('.source-name')" in html
