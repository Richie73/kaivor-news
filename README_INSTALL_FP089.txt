KAIVOR FP089 — STOCK PHOTO FALLBACK FOR IMAGELESS ARTICLES
==========================================================

PURPOSE
-------
Third of the polish pass: stories with no publisher picture get a
matching free stock photo (Openverse, no key needed), clearly
marked "Illustrative photo" with the photographer's credit, so it
never looks like the real event picture.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
   Openverse works without an API key for basic use.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
New:
- stock_images.py
- tests/test_stock_images_fp089.py
- CHANGELOG_FP089.txt
- README_INSTALL_FP089.txt
- BUNDLE_MANIFEST_FP089.txt

Replacement (back up the old copies as *.before-fp089 first):
- main.py
- news_store.py
- templates/index.html

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_stock_images_fp089.py -q
   Expect: 19 passed.

2. Full suite:
   python -m pytest -q
   Expect: 637 passed, 0 failed, 2 skipped (618 + 19 new).

PUSH
----
   cd ~/Kaivor
   git add stock_images.py main.py news_store.py templates/index.html tests/test_stock_images_fp089.py CHANGELOG_FP089.txt README_INSTALL_FP089.txt BUNDLE_MANIFEST_FP089.txt
   git status --short
   git commit -m "FP089: stock photo fallback for imageless articles"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Scroll the news: stories that had no picture now show a photo
  as they come into view, with "Illustrative photo" under it.
- Stories that already had a publisher picture are unchanged.
- Save a story with a stock photo: the Saved view shows the same
  "Illustrative photo" marking.
