README_INSTALL_FP126_3.txt — Independent puzzle links to the app's own host
===========================================================================

No database step.

Install: copy these files over the matching files in ~/Kaivor,
then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_puzzles_fp076.py tests/test_puzzle_app_links_fp126.py -q

Expected: 13 passed. Full suite: 1091 passed / 0 failed /
2 skipped.

Verify after deploy: the Independent card links to
intent://app.independent.co.uk/extras/puzzles#Intent;... in
the served page, and NO intent:#Intent;action=...MAIN...
launch intents remain. On the phone, tapping the Independent
card must open the Independent app (home screen, or the
puzzles section if the app routes the path), not the browser.
