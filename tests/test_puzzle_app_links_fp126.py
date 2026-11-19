"""FP126: puzzle cards open the puzzle's own Android app.

Puzzle links are Android intent URLs: the app opens when
installed, Chrome falls back to the web page when it is not.
Quordle has no official Android app, so it keeps a plain link.
"""

from urllib.parse import unquote, urlparse

import main
from news_store import deduplicate_articles


EXPECTED_APP_LINKS = {
    # title: (package, original web URL)
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
        link = by_title[title]["link"]
        assert link.startswith("intent://"), link
        assert f"package={package};" in link, link
        assert _fallback_of(link) == web_url, link


def test_quordle_keeps_a_plain_web_link():
    by_title = {item["title"]: item for item in main.puzzle_items()}
    assert by_title["Quordle - Daily Word Puzzle"]["link"] == "https://www.quordle.com"


def test_puzzle_links_survive_dedupe():
    items = main.puzzle_items()
    deduped = deduplicate_articles([dict(item) for item in items])
    assert len(deduped) == 12
    by_title = {item["title"]: item for item in deduped}
    for title, (package, _) in EXPECTED_APP_LINKS.items():
        assert by_title[title]["link"].startswith("intent://"), title
        assert f"package={package};" in by_title[title]["link"], title
    assert by_title["Quordle - Daily Word Puzzle"]["link"] == "https://www.quordle.com"


def test_card_label_prefers_app_for_intent_links():
    from pathlib import Path

    html = (
        Path(__file__).resolve().parent.parent / "templates" / "index.html"
    ).read_text()
    assert (
        '{% if article.link.startswith("intent://") %}Open in app{% else %}Open in Chrome{% endif %}'
        in html
    )
    assert (
        '${article.link.startsWith("intent://") ? "Open in app" : "Open in Chrome"}'
        in html
    )
