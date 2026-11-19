README_INSTALL_FP125_3.txt — Shopping items get a proper Delete button
==========================================================================

No database step.

Install: copy these files over the matching files in ~/Kaivor,
then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_shopping_hub_fp125.py -q

Expected: 42 passed. Full suite: 1082 passed / 0 failed /
2 skipped.

Verify after deploy: each shopping item shows a red-outlined
Delete button on the line under its name; tapping it asks
"Delete this item from the watchlist?" before deleting.
