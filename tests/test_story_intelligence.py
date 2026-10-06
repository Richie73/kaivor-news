import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from story_intelligence import enrich_articles


def main():
    articles = [
        {"id": "a", "title": "Kyiv bridge hit in Russian drone attack", "description": "A bridge in Kyiv was struck by a drone.", "category": "World", "source": "BBC News"},
        {"id": "b", "title": "Russian drone attack hits Kyiv bridge", "description": "Footage shows the Kyiv bridge hit during a drone strike.", "category": "World", "source": "CNN"},
        {"id": "c", "title": "New Android phone launches with faster chip", "description": "A manufacturer announced a new Android device.", "category": "Technology", "source": "TechCrunch"},
    ]
    result = enrich_articles(articles)
    assert result[0]["cluster_id"] == result[1]["cluster_id"]
    assert result[0]["source_count"] == 2
    assert result[0]["related_count"] == 1
    assert result[0]["developing"] is True
    assert result[2]["source_count"] == 1
    assert result[2]["related_count"] == 0
    assert result[2]["cluster_id"] != result[0]["cluster_id"]
    print("✓ Story intelligence clustering")


if __name__ == "__main__":
    main()
