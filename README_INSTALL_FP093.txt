KAIVOR FP093 — OFFLINE READING
=============================

PURPOSE
-------
Opening the app with no signal used to show the browser's error
page. Now the last loaded stories are kept on the phone and the
app opens on them offline, with a slim banner saying how old
they are ("You're offline — showing stories from 14:32.").

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP092 is installed.

FILES
-----
New:
- tests/test_offline_reading_fp093.py
- CHANGELOG_FP093.txt
- README_INSTALL_FP093.txt
- BUNDLE_MANIFEST_FP093.txt

Replacement (back up the old copies as *.before-fp093 first):
- static/service-worker.js
- templates/index.html
- main.py
- tests/test_logo_splash_fp083.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_offline_reading_fp093.py -q
   Expect: 9 passed.

2. Full suite:
   python -m pytest -q
   Expect: 691 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add static/service-worker.js templates/index.html main.py tests/test_offline_reading_fp093.py tests/test_logo_splash_fp083.py CHANGELOG_FP093.txt README_INSTALL_FP093.txt BUNDLE_MANIFEST_FP093.txt
   git status --short
   git commit -m "FP093: offline reading (cached homepage + offline banner)"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app: open it once
while online, switch the phone to aeroplane mode, and open it
again — the last stories show, with the offline banner on top.
