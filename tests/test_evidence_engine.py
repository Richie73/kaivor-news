import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from evidence_engine import build_evidence_model, canonical_source, evidence_sentence

ARTICLES = [
    {"id": "a", "title": "Kyiv bridge hit", "description": "A bridge was struck.", "source": "BBC News", "link": "https://www.bbc.co.uk/news/example"},
    {"id": "b", "title": "Kyiv bridge hit", "description": "The same bridge was struck.", "source": "BBC", "link": "https://www.bbc.com/news/example2"},
    {"id": "c", "title": "Kyiv bridge hit", "description": "Reuters reports the strike.", "source": "Reuters", "link": "https://www.reuters.com/world/example"},
]

assert canonical_source(ARTICLES[0]) == "BBC News"
assert canonical_source(ARTICLES[1]) == "BBC News"
model = build_evidence_model(ARTICLES)
assert model["report_count"] == 3
assert model["source_count"] == 2
assert model["repeated_same_source_reports"] == 1
assert model["corroborated"] is True
assert model["evidence_status"] == "Corroborated — 2 independent sources"
assert "same source group" in evidence_sentence(build_evidence_model(ARTICLES[:2]))
print("✓ Evidence and corroboration engine")
