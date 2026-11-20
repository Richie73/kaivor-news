README_INSTALL_FP128.txt — No stock photos on puzzle cards
===========================================================

No database step. No new env var.

Install: copy these files over the matching files in ~/Kaivor,
then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_puzzle_no_stock_photo_fp128.py tests/test_stock_images_fp089.py -q

Expected: 46 passed (7 new + 39 existing). Full suite:
1111 passed / 0 failed / 2 skipped.

Verify after deploy: open the Puzzles view — no puzzle card
shows a photo. News cards without a publisher picture still
get a stock photo as before.
