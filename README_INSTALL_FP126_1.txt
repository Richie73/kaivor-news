README_INSTALL_FP126_1.txt — Puzzle app links survive the feed quality gate
===============================================================================

No database step.

Install: copy these files over the matching files in ~/Kaivor,
then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_puzzles_fp076.py tests/test_puzzle_app_links_fp126.py -q

Expected: 12 passed. Full suite: 1090 passed / 0 failed /
2 skipped.

Verify after deploy: the Puzzles section shows all 12 puzzles
again, and 11 of them link to intent:// URLs (check the served
page for "intent://" and "Open in app"). Quordle stays a plain
web link.
