KAIVOR FP088 — LOADING STATES: SKELETON SCREENS
=============================================

PURPOSE
-------
Second of the polish pass: no more blank feed after a deploy and no
more "Loading…" text — shimmering placeholder cards and rows show
while the news, weather and markets load.

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
- tests/test_loading_skeletons_fp088.py
- CHANGELOG_FP088.txt
- README_INSTALL_FP088.txt
- BUNDLE_MANIFEST_FP088.txt

Replacement (back up the old copies as *.before-fp088 first):
- templates/index.html
- tests/test_logo_splash_fp083.py
- tests/test_settings_fp085.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_loading_skeletons_fp088.py tests/test_logo_splash_fp083.py tests/test_settings_fp085.py -q
   Expect: 23 passed.

2. Full suite:
   python -m pytest -q
   Expect: 618 passed, 0 failed, 2 skipped (612 + 6 new).

PUSH
----
   cd ~/Kaivor
   git add templates/index.html tests/test_loading_skeletons_fp088.py tests/test_logo_splash_fp083.py tests/test_settings_fp085.py CHANGELOG_FP088.txt README_INSTALL_FP088.txt BUNDLE_MANIFEST_FP088.txt
   git status --short
   git commit -m "FP088: loading states — skeleton screens"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Right after a deploy, the news shows grey placeholder cards
  instead of a blank list, then the stories appear on their own.
- The weather strip and hero shimmer briefly while loading.
- The Markets view opens with grey rows while history loads.
