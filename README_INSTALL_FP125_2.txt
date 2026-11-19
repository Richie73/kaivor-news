README_INSTALL_FP125_2.txt — Shopping links use a readable colour
==================================================================

No database step.

Install: copy these files over the matching files in ~/Kaivor,
then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_shopping_hub_fp125.py -q

Expected: 42 passed. Full suite: 1082 passed / 0 failed /
2 skipped.

Verify after deploy: the shopping item names in the Hub show
in light blue, readable on the dark background, visited or not.
