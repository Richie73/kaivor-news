from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from evidence_engine import build_evidence_model, evidence_sentence

BBC_1 = {"id": "a", "title": "Kyiv bridge hit", "description": "Bridge struck.", "source": "BBC News", "link": "https://bbc.co.uk/news/a"}
BBC_2 = {"id": "b", "title": "Kyiv bridge hit again", "description": "More footage.", "source": "BBC", "link": "https://bbc.com/news/b"}
REUTERS = {"id": "c", "title": "Kyiv bridge hit", "description": "Reuters reports strike.", "source": "Reuters", "link": "https://reuters.com/world/c"}

single = build_evidence_model([BBC_1])
assert "Source: BBC News" in evidence_sentence(single)

same_source = build_evidence_model([BBC_1, BBC_2])
text = evidence_sentence(same_source)
assert "same source group" in text
assert "not independent corroboration" in text
assert "Source: BBC News" in text

multi = build_evidence_model([BBC_1, BBC_2, REUTERS])
text = evidence_sentence(multi)
assert "2 independent source groups" in text
assert "Sources: BBC News, Reuters" in text

print("✓ Evidence clarity and source transparency")
