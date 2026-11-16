KAIVOR FP100 — RAMS DRAFTING
============================

PURPOSE
-------
Draft a Risk Assessment and Method Statement on the standard
template. Describe the task, tick the hazards, and Kaivor
drafts the method statement and risk assessment — you review
and edit every line before saving, and print it for site use.

IMPORTANT NOTES
---------------
1. No configuration changes are needed: drafting uses the
   OpenRouter or OpenAI key already set on the server. No PIN
   or secret changes, no key rotation needed for this
   milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP102 is installed.

FILES
-----
New:
- rams_library.py
- rams_drafter.py
- tests/test_rams_drafting_fp100.py
- CHANGELOG_FP100.txt
- README_INSTALL_FP100.txt
- BUNDLE_MANIFEST_FP100.txt

Replacement (back up the old copy as *.before-fp100 first):
- news_store.py
- main.py
- templates/index.html
- tests/test_weather_redesign_fp082.py
- tests/test_markets_view_fp086.py
- tests/test_morning_hub_fp101.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_rams_drafting_fp100.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py tests/test_morning_hub_fp101.py -q
   Expect: 45 passed.

2. Full suite:
   python -m pytest -q
   Expect: 765 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add rams_library.py rams_drafter.py news_store.py main.py templates/index.html tests/test_rams_drafting_fp100.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py tests/test_morning_hub_fp101.py CHANGELOG_FP100.txt README_INSTALL_FP100.txt BUNDLE_MANIFEST_FP100.txt
   git status --short
   git commit -m "FP100: RAMS drafting on a standard template"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Unlock via the 📚 Reading tab
first (drafting needs the app unlocked), then open the Hub and
tap "📋 Draft a RAMS". Describe a task, tick a few hazards,
generate the draft, and check the editor: steps, risk rows with
live risk bands, PPE. Save it, reopen it from the list, and try
"🖨️ Print / save as PDF" — the printout should be the clean
document only, with the sign-off table at the bottom.
