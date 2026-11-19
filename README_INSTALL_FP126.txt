README_INSTALL_FP126.txt — Puzzle cards open the puzzle's own Android app
=============================================================================

No database step.

Install: copy these files over the matching files in ~/Kaivor,
then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_puzzles_fp076.py tests/test_puzzle_app_links_fp126.py -q

Expected: 11 passed. Full suite: 1089 passed / 0 failed /
2 skipped.

Verify after deploy: the Puzzles cards link to intent:// URLs
(check one card's link in the served page or the API); on the
phone, tapping a puzzle opens its app when installed and the
web page when not. Quordle stays a web link (no official app).
