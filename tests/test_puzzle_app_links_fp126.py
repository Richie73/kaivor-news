"""FP126/FP126.1: puzzle cards open the puzzle's own Android app.

The app link rides in a separate "app_link" field as an Android
intent URL: the app opens when installed, Chrome falls back to
the web page when it is not. "link" stays the plain web URL —
FP126 first put the intent URL in "link" itself, but the feed
quality gate rejects any link whose scheme is not http(s), so
all 11 app-linked puzzles were dropped from the live feed and
only Quordle survived. Quordle has no official Android app, so
it has no app_link at all.
"""

from urllib.parse import unquote

import main
from news_feed_quality import assess_feed
from news_store import deduplicate_articles


EXPECTED_APP_LINKS = {
    # title: (package, web URL)
    "The New York Times - Wordle Daily Challenge": (
        "com.nytimes.crossword",
        "https://www.nytimes.com/games/wordle/index.html",
    ),
    "The Guardian - Daily Crossword Hub": (
        "com.guardian",
        "https://www.theguardian.com/crosswords",
    ),
    "The Independent - Daily Crosswords & Sudoku": (
        "com.freerange360.mpp.indy",
        "https://www.independent.co.uk/extras/puzzles",
    ),
    "The New York Times - Mini Crossword": (
        "com.nytimes.crossword",
        "https://www.nytimes.com/crosswords/game/mini",
    ),
    "The New York Times - Connections": (
        "com.nytimes.crossword",
        "https://www.nytimes.com/games/connections",
    ),
    "The New York Times - Strands": (
        "com.nytimes.crossword",
        "https://www.nytimes.com/games/strands",
    ),
    "Nerdle - Daily Numbers Game": (
        "com.nerdle.app",
        "https://www.nerdlegame.com",
    ),
    "Sudoku.com - Daily Sudoku": (
        "com.easybrain.sudoku.android",
        "https://sudoku.com",
    ),
    "Lichess - Chess Puzzles": (
        "org.lichess.mobileV2",
        "https://lichess.org/training",
    ),
    "Worldle - Guess the Country": (
        "fr.teuteuf.worldle.twa",
        "https://worldle.teuteuf.fr",
    ),
    "Waffle - Daily Word Game": (
        "net.wafflegame.waffle",
        "https://wafflegame.net",
    ),
}


def _fallback_of(intent_url):
    assert intent_url.startswith("intent://"), intent_url
    fragment = intent_url.split("#Intent;", 1)[1]
    assert fragment.endswith(";end"), intent_url
    parts = dict(
        piece.split("=", 1) for piece in fragment[:-4].split(";") if "=" in piece
    )
    return unquote(parts["S.browser_fallback_url"])


def test_app_link_builds_intent_url():
    assert main.app_link(
        "https://www.theguardian.com/crosswords", "com.guardian"
    ) == (
        "intent://www.theguardian.com/crosswords"
        "#Intent;scheme=https;package=com.guardian;"
        "S.browser_fallback_url=https%3A%2F%2Fwww.theguardian.com%2Fcrosswords;end"
    )


def test_app_link_defaults_to_root_path():
    assert main.app_link("https://sudoku.com", "com.easybrain.sudoku.android") == (
        "intent://sudoku.com/"
        "#Intent;scheme=https;package=com.easybrain.sudoku.android;"
        "S.browser_fallback_url=https%3A%2F%2Fsudoku.com;end"
    )


def test_app_link_fallback_decodes_to_the_web_url():
    url = "https://www.nytimes.com/games/wordle/index.html"
    assert _fallback_of(main.app_link(url, "com.nytimes.crossword")) == url


def test_puzzle_app_links():
    by_title = {item["title"]: item for item in main.puzzle_items()}
    assert set(EXPECTED_APP_LINKS).issubset(set(by_title))
    for title, (package, web_url) in EXPECTED_APP_LINKS.items():
        item = by_title[title]
        assert item["link"] == web_url, title
        app_link = item["app_link"]
        assert app_link.startswith("intent://"), title
        assert f"package={package};" in app_link, title
        assert _fallback_of(app_link) == web_url, title


def test_quordle_has_no_app_link():
    by_title = {item["title"]: item for item in main.puzzle_items()}
    item = by_title["Quordle - Daily Word Puzzle"]
    assert item["link"] == "https://www.quordle.com"
    assert not item.get("app_link")


def test_puzzle_app_links_survive_dedupe():
    items = main.puzzle_items()
    deduped = deduplicate_articles([dict(item) for item in items])
    assert len(deduped) == 12
    by_title = {item["title"]: item for item in deduped}
    for title, (package, web_url) in EXPECTED_APP_LINKS.items():
        item = by_title[title]
        assert item["link"] == web_url, title
        assert item["app_link"].startswith("intent://"), title
        assert f"package={package};" in item["app_link"], title
    assert by_title["Quordle - Daily Word Puzzle"]["link"] == "https://www.quordle.com"
    assert not by_title["Quordle - Daily Word Puzzle"].get("app_link")


def test_puzzle_app_links_survive_feed_quality_gate():
    # FP126.1 regression test: the gate rejects non-http(s) links,
    # which is what dropped every app-linked puzzle live. With the
    # intent URL in app_link and a plain web link, all 12 pass.
    report = assess_feed([dict(item) for item in main.puzzle_items()])
    assert report["accepted_count"] == 12
    assert report["rejected_count"] == 0
    by_title = {item["title"]: item for item in report["articles"]}
    for title, (package, web_url) in EXPECTED_APP_LINKS.items():
        assert by_title[title]["link"] == web_url, title
        assert by_title[title]["app_link"].startswith("intent://"), title
    assert not by_title["Quordle - Daily Word Puzzle"].get("app_link")


def test_card_links_prefer_app_link():
    from pathlib import Path

    html = (
        Path(__file__).resolve().parent.parent / "templates" / "index.html"
    ).read_text()
    assert '<a href="{{ article.app_link or article.link }}"' in html
    assert (
        '{% if article.app_link %}Open in app{% else %}Open in Chrome{% endif %}'
        in html
    )
    assert '<a href="${escapeAttr(article.app_link || article.link)}"' in html
    assert '${article.app_link ? "Open in app" : "Open in Chrome"}' in html
