KAIVOR FP097 — SPLASH LETS ITS ANIMATION FINISH
==============================================

PURPOSE
-------
The splash screen hid after 900ms — before its shine sweep had
finished, so the animation was cut off mid-sweep. It now stays
for 2 seconds so the logo animation plays through, then fades
out as before.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP096 is installed.

FILES
-----
New:
- tests/test_splash_polish_fp097.py
- CHANGELOG_FP097.txt
- README_INSTALL_FP097.txt
- BUNDLE_MANIFEST_FP097.txt

Replacement (back up the old copy as *.before-fp097 first):
- templates/index.html

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_splash_polish_fp097.py -q
   Expect: 3 passed.

2. Full suite:
   python -m pytest -q
   Expect: 710 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add templates/index.html tests/test_splash_polish_fp097.py CHANGELOG_FP097.txt README_INSTALL_FP097.txt BUNDLE_MANIFEST_FP097.txt
   git status --short
   git commit -m "FP097: splash stays 2s so its animation finishes"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then open the app fresh — the
logo should pop in, the shine should sweep across it, and only
then should it fade to the news.
