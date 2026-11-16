KAIVOR FP101 — MORNING HUB
=========================

PURPOSE
-------
One place to start the day: a greeting, the weather now, the
top five stories and a market snapshot, as a new 🌅 Hub tab
(first in the bottom bar). Calendar and live travel are not in
this version — they need the Google account connected to
Kaivor, which is a bigger job.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP099 is installed. (FP100 is
   still waiting on the RAMS template answer.)

FILES
-----
New:
- tests/test_morning_hub_fp101.py
- CHANGELOG_FP101.txt
- README_INSTALL_FP101.txt
- BUNDLE_MANIFEST_FP101.txt

Replacement (back up the old copy as *.before-fp101 first):
- templates/index.html
- templates/reading.html
- tests/test_bottom_nav_fp084.py
- tests/test_weather_redesign_fp082.py
- tests/test_markets_view_fp086.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_morning_hub_fp101.py tests/test_bottom_nav_fp084.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py -q
   Expect: 36 passed.

2. Full suite:
   python -m pytest -q
   Expect: 736 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add templates/index.html templates/reading.html tests/test_morning_hub_fp101.py tests/test_bottom_nav_fp084.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py CHANGELOG_FP101.txt README_INSTALL_FP101.txt BUNDLE_MANIFEST_FP101.txt
   git status --short
   git commit -m "FP101: morning hub — greeting, weather, top stories, markets"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then tap 🌅 Hub in the bottom
bar: greeting and date, the weather now, five top stories (tap
one to open it) and Gold / Bitcoin / £ → $ prices. Tap News,
Weather, Chat, Saved and Markets in turn — the hub should hide
cleanly each time, and Hub should hide each of them.
