KAIVOR FP092 — FASTER NEWS LIST
==============================

PURPOSE
-------
The news page renders every story into the DOM (600+ on a full
feed), which is heavy on a phone. Only the first 50 stories now
show, with a "Load more stories" button for the next 50, and
cards get content-visibility so off-screen ones are not painted
until they scroll into view.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP075.2 is pushed.

FILES
-----
New:
- tests/test_news_pagination_fp092.py
- CHANGELOG_FP092.txt
- README_INSTALL_FP092.txt
- BUNDLE_MANIFEST_FP092.txt

Replacement (back up the old copy as *.before-fp092 first):
- templates/index.html

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_news_pagination_fp092.py -q
   Expect: 8 passed.

2. Full suite:
   python -m pytest -q
   Expect: 682 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add templates/index.html tests/test_news_pagination_fp092.py CHANGELOG_FP092.txt README_INSTALL_FP092.txt BUNDLE_MANIFEST_FP092.txt
   git status --short
   git commit -m "FP092: faster news list (50 at a time + content-visibility)"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app, the news list
shows 50 stories with a "Load more stories" button underneath;
tapping it reveals the next 50. Picking a category starts back
at the first 50.
