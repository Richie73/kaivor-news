KAIVOR FP096 — TYPE SCALE + SPACING TIDY-UP
=========================================

PURPOSE
-------
Design system, part 2. Text sizes (15 distinct sizes before)
and spacing now use shared tokens on both pages, so the whole
app reads as one design. A few sizes converge to the nearest
step (9px badges to 10px, 15/17px headings to 16px) — barely
visible, but the type now sits on one scale.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP095 is installed.

FILES
-----
New:
- tests/test_type_scale_fp096.py
- CHANGELOG_FP096.txt
- README_INSTALL_FP096.txt
- BUNDLE_MANIFEST_FP096.txt

Replacement (back up the old copies as *.before-fp096 first):
- templates/index.html
- templates/reading.html
- tests/test_markets_view_fp086.py
- tests/test_news_cards_fp087.py
- tests/test_stock_images_fp089.py
- tests/test_design_system_fp090.py
- tests/test_loading_skeletons_fp088.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_type_scale_fp096.py tests/test_markets_view_fp086.py tests/test_news_cards_fp087.py tests/test_stock_images_fp089.py tests/test_design_system_fp090.py tests/test_loading_skeletons_fp088.py -q
   Expect: 74 passed.

2. Full suite:
   python -m pytest -q
   Expect: 707 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add templates/index.html templates/reading.html tests/test_type_scale_fp096.py tests/test_markets_view_fp086.py tests/test_news_cards_fp087.py tests/test_stock_images_fp089.py tests/test_design_system_fp090.py tests/test_loading_skeletons_fp088.py CHANGELOG_FP096.txt README_INSTALL_FP096.txt BUNDLE_MANIFEST_FP096.txt
   git status --short
   git commit -m "FP096: type scale + spacing tidy-up"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app, the pages
should look the same as before — same sizes, same spacing —
just more consistent: badges, headings and descriptions all sit
on one scale.
