KAIVOR FP086.1 — MARKETS: FILL THE STRIP + FOUR MORE ROWS
=====================================================

PURPOSE
-------
Two follow-ups to FP086: (1) when the Markets view loads, it now
also fills the home-page Market Watch strip's prices, so the strip
no longer says "No live data yet" after the view has loaded;
(2) four more rows in the Markets view — Silver, Ethereum, FTSE 100
and GBP/JPY — taking it from seven rows to eleven. The new rows are
view-only; the live ticker and the chat hub stay at seven assets.

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
- CHANGELOG_FP0861.txt
- README_INSTALL_FP0861.txt
- BUNDLE_MANIFEST_FP0861.txt

Replacement (back up the old copies as *.before-fp0861 first):
- main.py
- templates/index.html
- tests/test_markets_history_fp086.py
- tests/test_markets_view_fp086.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_markets_history_fp086.py tests/test_markets_view_fp086.py tests/test_weather_redesign_fp082.py -q
   Expect: 29 passed (8 FP086 server + 10 FP086 view + 11 FP082).

2. Full suite:
   python -m pytest -q
   Expect: 607 passed, 0 failed, 2 skipped (604 + 3 new).

PUSH
----
   cd ~/Kaivor
   git add main.py templates/index.html tests/test_markets_history_fp086.py tests/test_markets_view_fp086.py CHANGELOG_FP0861.txt README_INSTALL_FP0861.txt BUNDLE_MANIFEST_FP0861.txt
   git status --short
   git commit -m "FP086.1: fill the strip from the Markets view + four more rows"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Tap the Market Watch strip: eleven rows now — Silver after Gold,
  Ethereum after Bitcoin, FTSE 100 after the S&P 500, GBP/JPY with
  the currency pairs.
- Tap News: the strip now shows the prices instead of
  "No live data yet".
