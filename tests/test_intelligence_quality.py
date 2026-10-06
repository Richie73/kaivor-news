from story_intelligence import enrich_articles

ARTICLES = [
    {"id": "a", "title": "Kyiv bridge hit in Russian drone attack", "description": "A drone hit a bridge in Kyiv.", "category": "World", "source": "BBC News", "link": "https://example/a"},
    {"id": "b", "title": "Russian drone strikes Kyiv bridge", "description": "Footage shows a strike on the same Kyiv bridge.", "category": "World", "source": "Reuters", "link": "https://example/b"},
    {"id": "c", "title": "Watch: What we know about Russian strikes on Kyiv bridges", "description": "BBC reports on the bridge strikes.", "category": "World", "source": "BBC News", "link": "https://example/c"},
]

enriched = enrich_articles(ARTICLES)
assert len({item["cluster_id"] for item in enriched}) == 1, "Expected related Kyiv reports to cluster"
assert all(item["source_count"] == 2 for item in enriched), "Same-source reports must not count as independent corroboration"
assert all(item["report_count"] == 3 for item in enriched), "Expected three related reports"
assert all(item["evidence_status"] == "Corroborated — 2 independent sources" for item in enriched)
assert all("infrastructure" in item["impact_hint"].lower() or "conflict" in item["impact_hint"].lower() for item in enriched)
assert all(item["uncertainty_hint"] for item in enriched), "Expected an explicit uncertainty statement"
print("✓ Intelligence quality and evidence model")
