KAIVOR FP082 — WEATHER REDESIGN: SLIM STRIP + FULL WEATHER CATEGORY
=================================================================

PURPOSE
-------
The home page gets a slim one-line weather strip (place, temp,
condition, today's summary — tap it to open the forecast), and the
full forecast becomes its own 🌤️ Weather category: a big-temp
hero with feels-like and today's high/low, a details grid (wind +
gusts, humidity, rain, sunrise/sunset), the summary, the 12-hour
strip, and the 7 days as a clean vertical list.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. No new cost or keys — still Open-Meteo, fetched free by the
   browser. The forecast request now also asks for sunrise and
   sunset (same free call).
3. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
Replacement (back up the old copy as *.before-fp082 first):
- templates/index.html
- tests/test_weather_section_fp073.py
- tests/test_weather_upgrades_fp074.py

New:
- tests/test_weather_redesign_fp082.py
- CHANGELOG_FP082.txt
- README_INSTALL_FP082.txt
- BUNDLE_MANIFEST_FP082.txt

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_weather_redesign_fp082.py tests/test_weather_section_fp073.py tests/test_weather_upgrades_fp074.py -q
   Expect: 25 passed.

2. Full suite:
   python -m pytest -q
   Expect: 559 passed, 0 failed, 2 skipped (548 + 11 new).

PUSH
----
   cd ~/Kaivor
   git add templates/index.html tests/test_weather_redesign_fp082.py tests/test_weather_section_fp073.py tests/test_weather_upgrades_fp074.py CHANGELOG_FP082.txt README_INSTALL_FP082.txt BUNDLE_MANIFEST_FP082.txt
   git status --short
   git commit -m "FP082: slim weather strip + full Weather category"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Home shows a slim one-line weather strip under the chips.
  The news starts much higher up the page than before.
- Tap the strip (or the 🌤️ Weather chip): the full forecast
  opens — big temperature, details grid, 12-hour strip, 7-day
  list, search and recents.
- Tap Top Stories (or any news category): the news comes straight
  back, no reload needed. Swipe between categories to check
  Weather is in the swipe order.
