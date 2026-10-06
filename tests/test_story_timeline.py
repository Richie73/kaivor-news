import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from story_timeline import build_story_timeline, parse_published

ARTICLES = [
    {
        "id": "a",
        "title": "Initial report on Kyiv bridge strike",
        "description": "A bridge was struck.",
        "source": "BBC News",
        "published": "Mon, 05 Oct 2026 06:00:00 GMT",
        "link": "https://example.com/a",
    },
    {
        "id": "b",
        "title": "Reuters reports further details on Kyiv bridge strike",
        "description": "Reuters reports further details about the bridge strike.",
        "source": "Reuters",
        "published": "2026-10-05T07:30:00Z",
        "link": "https://example.com/b",
    },
    {
        "id": "c",
        "title": "BBC follow-up on Kyiv bridge strike",
        "description": "BBC provides additional footage and details.",
        "source": "BBC News",
        "published": "2026-10-05T09:00:00Z",
        "link": "https://example.com/c",
    },
]

timeline = build_story_timeline(ARTICLES)

assert parse_published("2026-10-05T07:30:00Z") is not None
assert timeline["report_count"] == 3
assert timeline["story_status"] == "Developing"
assert timeline["timeline"][0]["source"] == "BBC News"
assert timeline["timeline"][-1]["source"] == "BBC News"
assert timeline["timeline"][-1]["is_latest"] is True
assert timeline["timeline"][1]["coverage_type"] == "Additional report"
assert timeline["timeline"][2]["coverage_type"] in {"Follow-up coverage", "Repeat coverage", "Additional report"}
assert "latest report" in timeline["change_summary"]

print("✓ Story evolution and timeline engine")
