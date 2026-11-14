KAIVOR FP085.1 — TAPPING NEWS AFTER SAVED, CHAT OR SETTINGS BRINGS THE STORIES BACK
==================================================================================

PURPOSE
-------
Fixes a navigation bug found by the FP085 live check: after opening
Saved, Chat or Settings, tapping a news category (or News in the
bottom bar) did not bring the stories back — the view stayed in
place, or the list went blank. Only a page reload worked. The fix
caches the news HTML before a view replaces it and restores it
when a news category is picked.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. Install AFTER FP085 is pushed. Both milestones replace
   templates/index.html — install FP085.1 only once the FP085
   commit is on GitHub, so the two milestones stay separate.
3. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
New:
- tests/test_back_to_news_fp0851.py
- CHANGELOG_FP0851.txt
- README_INSTALL_FP0851.txt
- BUNDLE_MANIFEST_FP0851.txt

Replacement (back up the old copy as *.before-fp0851 first):
- templates/index.html

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_back_to_news_fp0851.py -q
   Expect: 5 passed.

2. Full suite:
   python -m pytest -q
   Expect: 589 passed, 0 failed, 2 skipped (584 + 5 new).

PUSH
----
   cd ~/Kaivor
   git add templates/index.html tests/test_back_to_news_fp0851.py CHANGELOG_FP0851.txt README_INSTALL_FP0851.txt BUNDLE_MANIFEST_FP0851.txt
   git status --short
   git commit -m "FP085.1: back to news after Saved, Chat and Settings"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Open Settings, then tap News in the bottom bar: the stories
  come straight back.
- Open Chat, then tap a category (e.g. World): the World stories
  show.
- Open Saved, then tap News: the stories come straight back.
