README_INSTALL_FP125_1.txt — Fire Stick check moves Currys → Argos
=================================================================

No database step: the live row repairs itself on the first Hub
open after deploy (repair_seed_urls, matched on the old URL).

Install: copy these files over the matching files in ~/Kaivor,
then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_shopping_hub_fp125.py -q

Expected: 42 passed. Full suite: 1082 passed / 0 failed /
2 skipped.

Verify after deploy: GET /api/shopping shows the Fire Stick
with store Argos and the argos.co.uk URL; tapping Check prices
in the Hub (unlocked) updates its last_checked.
