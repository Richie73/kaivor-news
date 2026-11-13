KAIVOR FP073 — WEATHER SECTION
==============================

PURPOSE
-------
Kaivor News had no weather at all — just a "Coming soon" stub and a
fake 15°C buried in the market data that was never even shown. This
milestone adds a real weather section to the news page: current
conditions and a 3-day forecast for home (Puddington, Wirral), plus a
search box to check any other place by name, with recent places
remembered for one-tap switching.

The weather data comes from Open-Meteo, which is free and needs no
API key. Your browser fetches it directly — nothing new runs on the
server, and no keys or settings are involved.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN or
   secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).
3. The weather needs an internet connection in the browser. If the
   fetch fails (offline, or Open-Meteo unreachable), the section says
   "Weather unavailable" instead of showing made-up numbers.

FILES
-----
Replacement (back up the old copies as *.before-fp073 first):
- templates/index.html
- main.py

New:
- tests/test_weather_section_fp073.py
- README_INSTALL_FP073.txt
- CHANGELOG_FP073.txt
- BUNDLE_MANIFEST_FP073.txt

INSTALL (TERMUX)
----------------
The install is done over SSH by Muse (the usual FP068/FP069 pattern):
copies are transferred, checksummed, and the replaced files are backed
up as *.before-fp073. No files are deleted.

VERIFY (TERMUX)
---------------
Run the targeted tests, then the full suite:

  cd ~/Kaivor
  python3 -m pytest tests/test_weather_section_fp073.py -q
  python3 -m pytest -q

Expected: the targeted run passes fully (the node logic test runs if
node is installed, and skips cleanly if it is not), and the full
suite passes with 0 failures on the phone.

Then check the fix by eye on the live site (after the Render deploy):
the weather section sits between the category chips and Top Stories,
showing Puddington, Wirral with the current temperature and a 3-day
forecast. Type a place name in the search box (e.g. Manchester) and
tapping a result should switch the weather to that place.

ROLLBACK
--------
Restore the backed-up files and restart the app:

  cd ~/Kaivor
  cp templates/index.html.before-fp073 templates/index.html
  cp main.py.before-fp073 main.py
  rm tests/test_weather_section_fp073.py

The weather section disappears and the old market fallback returns
(including its unused fake 15°C).

DEPLOY
------
After the Termux install and checks pass, commit and push the normal
way (Richie runs the push from Termux). Then CHECK the Render
dashboard: the FP071 push on 13 Nov did NOT auto-deploy, and the new
version only went live after a manual deploy from the dashboard
(Deploy -> Deploy latest commit). If no deploy starts within a few
minutes of the push, deploy it manually.
