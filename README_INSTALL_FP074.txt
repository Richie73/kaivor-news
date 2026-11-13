KAIVOR FP074 — WEATHER UPGRADES
==============================

PURPOSE
-------
FP073 added the weather section, but it was basic: current conditions
and 3 days. This milestone makes it properly useful for a working
day:

- The next 12 hours, hour by hour — temperature and rain chance, so
  you can see when rain starts and stops.
- Wind gusts next to the wind speed.
- A 7-day forecast instead of 3.
- A one-line summary at the top, like "Dry until 2pm, then rain."

Still Open-Meteo, still free, still no key.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN or
   secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).
3. The hourly strip and the summary need the hourly forecast. If it
   is missing, they stay blank rather than guessing.

FILES
-----
Replacement (back up the old copies as *.before-fp074 first):
- templates/index.html
- tests/test_weather_section_fp073.py

New:
- tests/test_weather_upgrades_fp074.py
- README_INSTALL_FP074.txt
- CHANGELOG_FP074.txt
- BUNDLE_MANIFEST_FP074.txt

INSTALL (TERMUX)
----------------
The install is done over SSH by Muse (the usual FP068/FP069 pattern):
copies are transferred, checksummed, and the replaced files are backed
up as *.before-fp074. No files are deleted.

VERIFY (TERMUX)
---------------
Run the targeted tests, then the full suite:

  cd ~/Kaivor
  python3 -m pytest tests/test_weather_upgrades_fp074.py tests/test_weather_section_fp073.py -q
  python3 -m pytest -q

Expected: the targeted run passes fully (the node logic tests run if
node is installed, and skip cleanly if it is not), and the full
suite passes with 0 failures on the phone.

Then check by eye on the live site (after the Render deploy): the
weather section should show a one-line summary under the place name,
an hourly strip for the next 12 hours, gusts next to the wind speed,
and a 7-day forecast you can scroll sideways.

ROLLBACK
--------
Restore the backed-up files and restart the app:

  cd ~/Kaivor
  cp templates/index.html.before-fp074 templates/index.html
  cp tests/test_weather_section_fp073.py.before-fp074 tests/test_weather_section_fp073.py
  rm tests/test_weather_upgrades_fp074.py

The weather section returns to the FP073 version (current + 3 days,
no hourly, no gusts, no summary).

DEPLOY
------
After the Termux install and checks pass, commit and push the normal
way (Richie runs the push from Termux). Then CHECK the Render
dashboard: the FP071 push on 13 Nov did NOT auto-deploy, and the new
version only went live after a manual deploy from the dashboard
(Deploy -> Deploy latest commit). If no deploy starts within a few
minutes of the push, deploy it manually.
