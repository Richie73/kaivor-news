KAIVOR FP090 — ONE DESIGN SYSTEM ACROSS ALL TABS
=================================================

PURPOSE
-------
Last of the polish pass: every tab now draws from one set of
design tokens (one palette, one set of corner sizes) instead of
the hardcoded colours and radii that grew milestone by milestone.
The look is the same, except a few corners converge on the shared
sizes (cards 13/14/16px all become 12px; small controls 7/9/10px
all become 8px). The Reading page's colours are aligned to match
the news page, so both pages read as one app.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).
3. SEQUENCING: install only after FP089 is pushed. FP090's
   template builds on FP089's template, so installing earlier
   would mix FP090's edits into FP089's commit. This installs
   together with FP089.1 (stock photo fix) in one batch — the two
   milestones touch different files except the shared test file,
   which carries both sets of changes. They push as one combined
   commit (see PUSH in README_INSTALL_FP0891.txt).

FILES
-----
New:
- tests/test_design_system_fp090.py
- CHANGELOG_FP090.txt
- README_INSTALL_FP090.txt
- BUNDLE_MANIFEST_FP090.txt

Replacement (back up the old copies as *.before-fp090 first):
- templates/index.html
- templates/reading.html
- tests/test_markets_view_fp086.py
- tests/test_bottom_nav_fp084.py
- tests/test_news_cards_fp087.py
- tests/test_loading_skeletons_fp088.py
- tests/test_stock_images_fp089.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_stock_images_fp089.py tests/test_design_system_fp090.py tests/test_markets_view_fp086.py tests/test_bottom_nav_fp084.py tests/test_news_cards_fp087.py tests/test_loading_skeletons_fp088.py -q
   Expect: 62 passed.

2. Full suite:
   python -m pytest -q
   Expect: 651 passed, 0 failed, 2 skipped (645 + 6 new FP089.1
   tests).

PUSH
----
One combined commit for FP089.1 + FP090 — see the script in
README_INSTALL_FP0891.txt.

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Every tab looks the same as before — same colours, same layout.
- Cards, weather panels and market panels all have the same
  corner size now; small buttons and inputs match too.
- Open the Reading tab: its panels and buttons match the news
  page's colours and corners.
