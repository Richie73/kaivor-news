KAIVOR FP089.4 — STOCK PHOTOS: TWO-LETTER KEYWORDS ALLOWLISTED
==============================================================

PURPOSE
-------
Fix for the one remaining FP089.3 live-check failure: a Levi's
wall mural on a Utah football story. The mural is titled
"Levi's Ad, Utah" — "AD" means Athletic Director in the
headline but advertisement in the photo's title, and "ad" plus
"utah" gave it two keyword hits. Two-letter words now only
count when they are unambiguous (AI, UK, US, TV, EU, UN).

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP089.3 is pushed. FP089.4's
   stock_images.py builds on FP089.3's.

FILES
-----
New:
- CHANGELOG_FP0894.txt
- README_INSTALL_FP0894.txt
- BUNDLE_MANIFEST_FP0894.txt

Replacement (back up the old copies as *.before-fp0894 first):
- stock_images.py
- tests/test_stock_images_fp089.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_stock_images_fp089.py -q
   Expect: 39 passed.

2. Full suite:
   python -m pytest -q
   Expect: 673 passed, 0 failed, 2 skipped (671 + 2 new).

PUSH
----
   cd ~/Kaivor
   git add stock_images.py tests/test_stock_images_fp089.py CHANGELOG_FP0894.txt README_INSTALL_FP0894.txt BUNDLE_MANIFEST_FP0894.txt
   git status --short
   git commit -m "FP089.4: two-letter keywords allowlisted"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app, scroll the
news and check:
- The Utah coaches story shows a sports photo (or no photo),
  never the Levi's mural.
- The screwdriver and NHL stories still show their good photos.
- Some cards stay picture-less — that is the fix working.
