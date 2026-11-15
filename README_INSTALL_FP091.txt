KAIVOR FP091 — WEATHER IMPROVEMENTS
==================================

PURPOSE
-------
Five improvements to the Weather view, from the weather proposal
assessment (15 Nov 2026): an attribution link to Open-Meteo, air
quality (European AQI + PM2.5), saved places you manage yourself,
a 24-hour strip and summary, and a 16-day forecast option.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
   The air-quality API is free with no key, like the forecast.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after the FP089.1 + FP090 combined
   commit is pushed. FP091's template builds on FP090's
   unpushed template, so installing earlier would mix FP091's
   edits into that commit.

FILES
-----
New:
- tests/test_weather_improvements_fp091.py
- CHANGELOG_FP091.txt
- README_INSTALL_FP091.txt
- BUNDLE_MANIFEST_FP091.txt

Replacement (back up the old copies as *.before-fp091 first):
- templates/index.html
- tests/test_weather_section_fp073.py
- tests/test_weather_upgrades_fp074.py
- tests/test_weather_redesign_fp082.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_weather_improvements_fp091.py tests/test_weather_section_fp073.py tests/test_weather_upgrades_fp074.py tests/test_weather_redesign_fp082.py -q
   Expect: 32 passed.

2. Full suite:
   python -m pytest -q
   Expect: 658 passed, 0 failed, 2 skipped (651 + 7 new).

PUSH
----
   cd ~/Kaivor
   git add templates/index.html tests/test_weather_improvements_fp091.py tests/test_weather_section_fp073.py tests/test_weather_upgrades_fp074.py tests/test_weather_redesign_fp082.py CHANGELOG_FP091.txt README_INSTALL_FP091.txt BUNDLE_MANIFEST_FP091.txt
   git status --short
   git commit -m "FP091: weather improvements — air quality, saved places, 24h strip, 16-day forecast"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app, open the
Weather view and check:
- The details grid shows Air quality (e.g. "34 · Fair") and
  PM2.5 below the Sun row.
- "Next 24 hours" above the hourly strip; the summary line
  covers 24 hours.
- A "Show 16 days" button above the forecast; tapping it shows
  16 days, tapping again goes back to 7.
- A ☆ Save button beside the refresh button; tapping it saves
  the place (★ Saved) and it appears under "Saved places:"
  below the search. Tap a saved place to load it; ✎ renames
  it, ↑/↓ reorder it, ✕ removes it.
- At the bottom of the view: "Weather data by Open-Meteo ·
  Air quality by Open-Meteo Air Quality" with working links.
