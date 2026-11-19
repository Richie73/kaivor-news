"""FP076: more puzzles in the Puzzles category."""

import main


EXPECTED_NEW_TITLES = {
    "The New York Times - Connections",
    "The New York Times - Strands",
    "Quordle - Daily Word Puzzle",
    "Nerdle - Daily Numbers Game",
    "Sudoku.com - Daily Sudoku",
    "Lichess - Chess Puzzles",
    "Worldle - Guess the Country",
    "Waffle - Daily Word Game",
}


def test_puzzle_list_has_twelve_entries():
    items = main.puzzle_items()
    assert len(items) == 12
    titles = {item["title"] for item in items}
    assert EXPECTED_NEW_TITLES.issubset(titles)


def test_every_puzzle_entry_is_complete():
    for item in main.puzzle_items():
        assert item["category"] == "Puzzles"
        assert item["title"].strip()
        assert item["description"].strip()
        assert item["source"].strip()
        assert item["published"] == "Daily"
        link = item["link"]
        assert link.startswith("https://"), link


def test_puzzle_links_are_unique():
    links = [item["link"] for item in main.puzzle_items()]
    assert len(links) == len(set(links))


def test_puzzle_titles_are_unique():
    titles = [item["title"] for item in main.puzzle_items()]
    assert len(titles) == len(set(titles))
