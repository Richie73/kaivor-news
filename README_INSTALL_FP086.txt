KAIVOR FP086 — FULL MARKETS VIEW + PRICE HISTORY
==============================================

PURPOSE
-------
Tapping the Market Watch strip opens a full Markets view: one row
per asset with the current price, today's change, a five-trading-day
sparkline and the day's (or five-day) range. History comes from
Yahoo Finance and Frankfurter on demand — no storage, no new keys.

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
- tests/test_markets_history_fp086.py
- tests/test_markets_view_fp086.py
- CHANGELOG_FP086.txt
- README_INSTALL_FP086.txt
- BUNDLE_MANIFEST_FP086.txt

Replacement (back up the old copies as *.before-fp086 first):
- main.py
- templates/index.html
- tests/test_weather_redesign_fp082.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_markets_history_fp086.py tests/test_markets_view_fp086.py tests/test_weather_redesign_fp082.py -q
   Expect: 26 passed (8 FP086 server + 7 FP086 view + 11 FP082).

2. Full suite:
   python -m pytest -q
   Expect: 604 passed, 0 failed, 2 skipped (589 + 15 new).

PUSH
----
   cd ~/Kaivor
   git add main.py templates/index.html tests/test_markets_history_fp086.py tests/test_markets_view_fp086.py tests/test_weather_redesign_fp082.py CHANGELOG_FP086.txt README_INSTALL_FP086.txt BUNDLE_MANIFEST_FP086.txt
   git status --short
   git commit -m "FP086: full Markets view + price history"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Tap the Market Watch strip: the Markets view opens with seven
  rows — price, today's change, a sparkline and a range each.
- Tap News in the bottom bar: the stories come straight back.
- Tap the strip again, then ↻ Refresh: the numbers update.
