KAIVOR FP086.2 — MARKETS STRIP STATUS UPDATES AT ONCE
===================================================

PURPOSE
-------
Fix for a gap found by FP086.1's live check: after the Markets view
filled the strip's prices, the status text still read "No live data
yet — tap Refresh markets" until the next 30-second ticker poll.
The status now updates the moment the strip fills.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
New:
- CHANGELOG_FP0862.txt
- README_INSTALL_FP0862.txt
- BUNDLE_MANIFEST_FP0862.txt

Replacement (back up the old copies as *.before-fp0862 first):
- templates/index.html
- tests/test_markets_view_fp086.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_markets_view_fp086.py -q
   Expect: 10 passed.

2. Full suite:
   python -m pytest -q
   Expect: 607 passed, 0 failed, 2 skipped (no new tests).

PUSH
----
   cd ~/Kaivor
   git add templates/index.html tests/test_markets_view_fp086.py CHANGELOG_FP0862.txt README_INSTALL_FP0862.txt BUNDLE_MANIFEST_FP0862.txt
   git status --short
   git commit -m "FP086.2: markets strip status updates at once"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Tap the Market Watch strip, then tap News: the strip shows the
  prices AND the status reads "Prices from the Markets view"
  straight away — no more "No live data yet" while prices show.
