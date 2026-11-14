KAIVOR FP083 — LOGO REFRESH (SPARK K) + SPLASH SCREEN
====================================================

PURPOSE
-------
The app icon is refreshed to the Spark K mark (bold black K +
spark, same green as before), shown in the header on both pages
and used for the home-screen icon and favicon. Opening the app
now shows a short splash screen — logo, wordmark and an animated
loading bar — that fades away once the page is usable.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. The old v2 icon files are left in place, unreferenced. The
   service worker drops the old v2 cache itself on activation.
3. The home-screen icon on the phone updates when the installed
   app next checks the manifest — it may take a reopen or two
   before the new icon appears. The in-app header mark and the
   splash screen change immediately.
4. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
New:
- static/icons/kaivor-news-192-v3.png
- static/icons/kaivor-news-512-v3.png
- static/icons/kaivor-logo-v3.svg
- tests/test_logo_splash_fp083.py
- CHANGELOG_FP083.txt
- README_INSTALL_FP083.txt
- BUNDLE_MANIFEST_FP083.txt

Replacement (back up the old copies as *.before-fp083 first):
- static/manifest.webmanifest
- static/service-worker.js
- templates/index.html
- templates/reading.html
- tests/test_weather_section_fp073.py
- tests/test_weather_upgrades_fp074.py
- tests/test_weather_redesign_fp082.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_logo_splash_fp083.py tests/test_weather_section_fp073.py tests/test_weather_upgrades_fp074.py tests/test_weather_redesign_fp082.py -q
   Expect: 34 passed (9 FP083 + 8 FP073 + 6 FP074 + 11 FP082).

2. Full suite:
   python -m pytest -q
   Expect: 568 passed, 0 failed, 2 skipped (559 + 9 new).

PUSH
----
   cd ~/Kaivor
   git add static/icons/kaivor-news-192-v3.png static/icons/kaivor-news-512-v3.png static/icons/kaivor-logo-v3.svg static/manifest.webmanifest static/service-worker.js templates/index.html templates/reading.html tests/test_logo_splash_fp083.py tests/test_weather_section_fp073.py tests/test_weather_upgrades_fp074.py tests/test_weather_redesign_fp082.py CHANGELOG_FP083.txt README_INSTALL_FP083.txt BUNDLE_MANIFEST_FP083.txt
   git status --short
   git commit -m "FP083: Spark K logo + splash screen"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Reload the home page: the splash (logo + loading bar) shows
  briefly, then fades to the news.
- The header shows the new green/black logo next to KAIVOR NEWS.
- Open the Reading tab: same logo in its header.
- After dark, clear hours in the weather view show a moon, not
  a sun.
- The home-screen icon updates on its own over the next reopen
  or two.
