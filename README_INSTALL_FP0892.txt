KAIVOR FP089.2 — STOCK PHOTOS THAT MATCH THEIR STORY
====================================================

PURPOSE
-------
Fix for FP089.1, found live 15 Nov 2026 from Richie's
screenshots: photos were appearing, but the wrong ones (a
bulldog on an NFL story, a fighter jet on a college football
story). Each photo is now scored against its headline and its
category, and a photo that does not match is rejected — no
photo beats a wrong photo. Also fixes the 16th forecast day
showing a ❓ icon with 0° / 0° (found in FP091's live check).

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP091 is pushed. FP089.2's
   template builds on FP091's template.

FILES
-----
New:
- CHANGELOG_FP0892.txt
- README_INSTALL_FP0892.txt
- BUNDLE_MANIFEST_FP0892.txt

Replacement (back up the old copies as *.before-fp0892 first):
- stock_images.py
- main.py
- templates/index.html
- tests/test_stock_images_fp089.py
- tests/test_weather_improvements_fp091.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_stock_images_fp089.py tests/test_weather_improvements_fp091.py -q
   Expect: 40 passed.

2. Full suite:
   python -m pytest -q
   Expect: 666 passed, 0 failed, 2 skipped (658 + 8 new).

PUSH
----
   cd ~/Kaivor
   git add stock_images.py main.py templates/index.html tests/test_stock_images_fp089.py tests/test_weather_improvements_fp091.py CHANGELOG_FP0892.txt README_INSTALL_FP0892.txt BUNDLE_MANIFEST_FP0892.txt
   git status --short
   git commit -m "FP089.2: stock photos scored against headline and category"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app, scroll the
news and check:
- The Lions/Patriots story no longer shows the bulldog (it
  shows a football-related photo or no photo).
- The CFP Texas story no longer shows the fighter jet.
- Photos that were already on-topic (the UFC belt, the Dallas
  skyline) are unchanged.
- Some cards may stay picture-less — that is the fix working:
  a story with no matching photo gets none rather than a
  random one.
- In the Weather view, "Show 16 days" shows no ❓ 0° / 0° row.
