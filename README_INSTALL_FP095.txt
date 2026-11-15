KAIVOR FP095 — NEWS REFRESH BUTTON
=================================

PURPOSE
-------
A "Refresh news" button beside the section title pulls fresh
stories on demand. The refresh runs in the background (the old
route ran it inline and would have hung the tap for ~90s); the
page reloads once the new stories land.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP094 is installed.
4. Refreshing needs the app unlocked (PIN via Reading) — a locked
   tap says so instead of hanging.

FILES
-----
New:
- tests/test_news_refresh_button_fp095.py
- CHANGELOG_FP095.txt
- README_INSTALL_FP095.txt
- BUNDLE_MANIFEST_FP095.txt

Replacement (back up the old copies as *.before-fp095 first):
- main.py
- templates/index.html
- tests/test_news_mutation_auth_fp069.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_news_refresh_button_fp095.py tests/test_news_mutation_auth_fp069.py -q
   Expect: 48 passed.

2. Full suite:
   python -m pytest -q
   Expect: 701 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add main.py templates/index.html tests/test_news_refresh_button_fp095.py tests/test_news_mutation_auth_fp069.py CHANGELOG_FP095.txt README_INSTALL_FP095.txt BUNDLE_MANIFEST_FP095.txt
   git status --short
   git commit -m "FP095: news refresh button (background refresh + poll)"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app (unlocked),
tap "Refresh news" beside Top Stories — the status line says it
is refreshing, and the page reloads with fresh stories after
about a minute.
