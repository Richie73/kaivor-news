"""FP109: American-football and baseball stories are excluded from the feed.

The filter lives in news_store.deduplicate_articles, the single funnel every
refreshed article (RSS, Guardian, NewsData) passes through. Saved articles
are deliberately untouched.
"""
import pytest

import news_store
from news_store import deduplicate_articles, is_us_sport_story


def _article(title, description="", link="https://example.com/story"):
    return {"title": title, "description": description, "link": link}


@pytest.mark.parametrize(
    "title",
    [
        "Let's overreact to NFL Week 10: Cousins changes the NFC North?",
        "Are Bengals a Super Bowl threat?",
        "American football is growing fast in the UK",
        "College football playoff race heats up",
        "Patriots quarterback Drake Maye to miss extended time",
        "Gridiron greats gather for hall of fame weekend",
        "The Skubal Tiers: Every MLB team's likelihood of signing Tarik Skubal",
        "Dodgers win World Series in extra innings",
        "Baseball's new pace-of-play rules explained",
    ],
)
def test_each_term_in_title_is_dropped(title):
    assert is_us_sport_story(_article(title)) is True


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("Mahomes magic seals it in overtime", "The NFL star threw for 300 yards"),
        ("Skubal signs record deal", "The baseball pitcher agrees $200m terms"),
    ],
)
def test_term_in_description_only_is_dropped(title, description):
    assert is_us_sport_story(_article(title, description)) is True


@pytest.mark.parametrize(
    "link",
    [
        "https://www.espn.com/nfl/story/_/id/50500352/patriots-qb-maye",
        "https://www.espn.com/mlb/story/_/id/50454235/skubal-tiers",
        "https://www.bbc.com/sport/american-football/articles/cx2q3k4l5m6n",
        "https://www.theguardian.com/sport/baseball/2026/nov/16/story",
    ],
)
def test_league_url_path_is_dropped_even_with_neutral_title(link):
    assert is_us_sport_story(_article("Skubal Tiers: every team's backup plan", "", link)) is True


@pytest.mark.parametrize(
    "title",
    [
        "Two quarterbacks headline the draft class",
        "Baseballs used in the final sell for thousands",
    ],
)
def test_plurals_are_dropped(title):
    assert is_us_sport_story(_article(title)) is True


def test_world_series_of_darts_is_dropped_too():
    # Known trade-off (see news_store.py): "world series" cannot tell the
    # MLB finals from darts/poker events, and the MLB event is the one
    # Richie asked to exclude.
    assert is_us_sport_story(_article("World Series of Darts: Littler wins in Amsterdam")) is True


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("Arsenal beat Liverpool 2-1 at the Emirates", ""),
        ("Lakers win NBA thriller in overtime", ""),
        ("Touchdown confirmed for Mars lander", "The spacecraft touched down safely"),
        ("Chancellor's budget is a home run, say markets", ""),
        ("England name squad for the autumn internationals", ""),
    ],
)
def test_unrelated_stories_are_kept(title, description):
    assert is_us_sport_story(_article(title, description)) is False


def test_deduplicate_drops_us_sport_and_keeps_deduping():
    football = _article("Arsenal beat Liverpool 2-1 at the Emirates", "", "https://example.com/arsenal")
    articles = [
        football,
        dict(football),
        _article("Let's overreact to NFL Week 10", "", "https://example.com/nfl"),
        _article("Dodgers win World Series", "", "https://example.com/mlb"),
        _article("Lakers win NBA thriller in overtime", "", "https://example.com/nba"),
    ]
    result = deduplicate_articles(articles)
    assert [item["title"] for item in result] == [
        "Arsenal beat Liverpool 2-1 at the Emirates",
        "Lakers win NBA thriller in overtime",
    ]


def test_saved_articles_are_not_filtered(tmp_path, monkeypatch):
    # Saving keeps whatever the user saved, even a US-sport story.
    saved_file = tmp_path / "saved.json"
    monkeypatch.setattr(news_store, "SAVED_FILE", saved_file)
    nfl = _article("Let's overreact to NFL Week 10")
    news_store.save_article(nfl)
    assert [item["title"] for item in news_store.load_saved_articles()] == [
        "Let's overreact to NFL Week 10"
    ]
