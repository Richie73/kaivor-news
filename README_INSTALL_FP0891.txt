KAIVOR FP089.1 — STOCK PHOTO FALLBACK THAT ACTUALLY FINDS PHOTOS
===================================================================

PURPOSE
-------
Fix for FP089, found live 15 Nov 2026: the five-word keyword query
returned zero results from Openverse for most headlines, so almost
no card gained a photo even though the API endpoint worked. The
lookup now tries shorter queries until one hits (full set, then
proper nouns, then the single most distinctive word). Also fixes
feeds that show the literal word "null" as a story summary.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. This installs together with FP090 (design system) in one batch
   — the two milestones touch different files except the shared
   test file, which carries both sets of changes. They push as one
   combined commit (see PUSH).

FILES
-----
New:
- CHANGELOG_FP0891.txt
- README_INSTALL_FP0891.txt
- BUNDLE_MANIFEST_FP0891.txt

Replacement (back up the old copies as *.before-fp0891 first):
- stock_images.py
- news_store.py
- tests/test_stock_images_fp089.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse, together with FP090.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_stock_images_fp089.py tests/test_design_system_fp090.py tests/test_markets_view_fp086.py tests/test_bottom_nav_fp084.py tests/test_news_cards_fp087.py tests/test_loading_skeletons_fp088.py -q
   Expect: 62 passed.

2. Full suite:
   python -m pytest -q
   Expect: 651 passed, 0 failed, 2 skipped (645 + 6 new).

PUSH
----
One combined commit for FP089.1 + FP090 (the shared test file
carries both milestones' changes, so they land together):

   cd ~/Kaivor
   git add stock_images.py news_store.py templates/index.html templates/reading.html tests/test_stock_images_fp089.py tests/test_design_system_fp090.py tests/test_markets_view_fp086.py tests/test_bottom_nav_fp084.py tests/test_news_cards_fp087.py tests/test_loading_skeletons_fp088.py CHANGELOG_FP0891.txt README_INSTALL_FP0891.txt BUNDLE_MANIFEST_FP0891.txt CHANGELOG_FP090.txt README_INSTALL_FP090.txt BUNDLE_MANIFEST_FP090.txt
   git status --short
   git commit -m "FP089.1 + FP090: stock photo fallback fix and design system"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Scroll the news: stories with no publisher picture now gain a
  stock photo as they come into view, with "Illustrative photo"
  underneath. Far fewer picture-less cards than before.
- Stories that already had a publisher picture are unchanged.
- No story shows the literal word "null" as its summary.
