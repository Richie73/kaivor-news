README_INSTALL_FP126_2.txt — Independent and Waffle puzzles launch their apps
================================================================================

No database step.

Install: copy these files over the matching files in ~/Kaivor,
then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_puzzles_fp076.py tests/test_puzzle_app_links_fp126.py -q

Expected: 14 passed. Full suite: 1092 passed / 0 failed /
2 skipped.

Verify after deploy: the Independent and Waffle cards link to
intent:#Intent;action=android.intent.action.MAIN;... URLs in
the served page. On the phone, tapping the Independent card
must open the Independent app (home screen), not the browser.
