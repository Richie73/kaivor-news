KAIVOR FP103 — MORNING HUB V2: CALENDAR + LIVE TRAVEL
====================================================

PURPOSE
-------
The Morning Hub now shows today's calendar and live Wirral
travel (Merseyrail, M53/M56, A41, tunnels) alongside weather,
stories and markets.

IMPORTANT NOTES
---------------
1. The hub works without any setup, but the calendar and
   travel cards say "not set up yet" until the four keys are
   added in Render (see SETUP below). Nothing about the keys
   goes in chat — paste them in the Render dashboard only.
2. This milestone adds two Python packages
   (icalendar, recurring-ical-events). Install them in Termux
   before running the tests:
     pip install icalendar recurring-ical-events
   Render installs them from requirements.txt at deploy.
3. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
4. SEQUENCING: install only after FP100 is installed.

SETUP (in the Render dashboard, kaivor-news service)
----------------------------------------------------
1. KAIVOR_CALENDAR_ICS_URL — Google Calendar on the web →
   Settings → your calendar → "Integrate calendar" → copy
   "Secret address in iCal format" → paste as the value.
   (On the phone, use Chrome's "Desktop site" — the app
   doesn't show it.) Treat this URL like a password.
2. TRANSCAPI_API_KEY — free signup at transcapi.com (no
   card) → copy the API key.
3. NATIONAL_HIGHWAYS_API_KEY — free account at
   developer.data.nationalhighways.co.uk → subscribe to
   "Road and Lane Closures" → copy the key.
4. TOMTOM_API_KEY — free account at developer.tomtom.com
   → create an app → copy the API key.
Add each as a new environment variable on kaivor-news and
redeploy. Any you skip just leaves that card saying
"not set up yet".

FILES
-----
New:
- hub_services.py
- tests/test_morning_hub_v2_fp103.py
- CHANGELOG_FP103.txt
- README_INSTALL_FP103.txt
- BUNDLE_MANIFEST_FP103.txt

Replacement (back up the old copy as *.before-fp103 first):
- main.py
- templates/index.html
- requirements.txt
- render.yaml

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_morning_hub_v2_fp103.py tests/test_morning_hub_fp101.py -q
   Expect: 18 passed.

2. Full suite:
   python -m pytest -q
   Expect: 776 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add hub_services.py main.py templates/index.html requirements.txt render.yaml tests/test_morning_hub_v2_fp103.py CHANGELOG_FP103.txt README_INSTALL_FP103.txt BUNDLE_MANIFEST_FP103.txt
   git status --short
   git commit -m "FP103: morning hub v2 — calendar and live travel"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Open the Hub: the calendar
card asks you to unlock (📚 Reading tab) before it shows
events, and the travel card shows the setup note until the
keys above are added. After adding a key in Render, redeploy
and the card fills in.
