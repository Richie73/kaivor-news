from personal_relevance import calculate_personal_relevance, DEFAULT_PROFILE, _normalise_profile

profile = {
    "categories": {"Technology": 5, "World": 1},
    "keywords": ["AI", "construction"],
    "regions": ["UK"],
}

tech = {
    "category": "Technology",
    "title": "New AI construction software announced",
    "description": "A technology company released an artificial intelligence tool for construction teams.",
}
assessment = calculate_personal_relevance(tech, profile)
assert assessment["label"] == "High"
assert assessment["score"] >= 70
assert "AI" in assessment["matched_keywords"]
assert "construction" in assessment["matched_keywords"]

world = {
    "category": "World",
    "title": "International summit opens",
    "description": "Leaders meet for talks.",
}
assessment2 = calculate_personal_relevance(world, profile)
assert assessment2["score"] < assessment["score"]

uk = {
    "category": "UK",
    "title": "UK construction rules updated",
    "description": "New UK construction guidance affects businesses.",
}
assessment3 = calculate_personal_relevance(uk, profile)
assert assessment3["score"] > 40
assert "UK" in assessment3["matched_regions"]

normalised = _normalise_profile({"categories": {"Technology": 99}, "keywords": ["AI", "AI"], "regions": ["UK"]})
assert normalised["categories"]["Technology"] == 5
assert normalised["keywords"] == ["AI"]
print("✓ Personal relevance engine")
