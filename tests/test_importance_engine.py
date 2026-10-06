from datetime import datetime, timezone
from importance_engine import build_importance_model

base={"category":"World","source_count":1,"report_count":1,"published":"2026-10-05T08:00:00Z","title":"Bridge strike disrupts power infrastructure","description":"A bridge was hit in a military strike."}
model=build_importance_model([base], now=datetime(2026,10,5,10,0,tzinfo=timezone.utc), story_status="New")
assert model["importance"]["label"] == "High"
assert model["importance"]["score"] >= 75
assert model["confidence_assessment"]["label"] == "Low"

members=[dict(base, id="a", source_count=2, report_count=2), dict(base, id="b", source_count=2, report_count=2, source="Reuters")]
model2=build_importance_model(members, now=datetime(2026,10,5,10,0,tzinfo=timezone.utc), story_status="Developing")
assert model2["confidence_assessment"]["label"] == "Moderate"
assert model2["importance"]["score"] >= model["importance"]["score"]
print("✓ Story importance and confidence engine")
