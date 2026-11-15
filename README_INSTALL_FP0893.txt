KAIVOR FP089.3 — STOCK PHOTOS: DISTINCTIVE WORDS ONLY
=====================================================

PURPOSE
-------
Fix for FP089.2, found in its live check on 15 Nov 2026: two
photos in the first 20 cards were still wrong — a torso on a
screwdriver story and a TV cartoon on an NHL story. Both
matched generic headline words ("black", "friday", "pro",
"tonight", "sunday"). Queries and scoring now use only the
distinctive words of a headline, and a bare league acronym
("NFL" mentioned in passing) is no longer enough on its own.
Also renames the weather days toggle to "Show all days" (it
said 16 days but showed 15 when the last day had no data).

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP089.2 is pushed. FP089.3's
   template builds on FP089.2's template.

FILES
-----
New:
- CHANGELOG_FP0893.txt
- README_INSTALL_FP0893.txt
- BUNDLE_MANIFEST_FP0893.txt

Replacement (back up the old copies as *.before-fp0893 first):
- stock_images.py
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
   Expect: 45 passed.

2. Full suite:
   python -m pytest -q
   Expect: 671 passed, 0 failed, 2 skipped (666 + 5 new).

PUSH
----
   cd ~/Kaivor
   git add stock_images.py templates/index.html tests/test_stock_images_fp089.py tests/test_weather_improvements_fp091.py CHANGELOG_FP0893.txt README_INSTALL_FP0893.txt BUNDLE_MANIFEST_FP0893.txt
   git status --short
   git commit -m "FP089.3: stock photos use distinctive words only"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app, scroll the
news and check:
- The screwdriver story shows a screwdriver (or no photo),
  never the torso.
- The NHL story shows a hockey photo (or no photo), never the
  TV cartoon.
- The Lions/Patriots story shows an American football photo
  (or no photo), never the bulldog.
- Some cards stay picture-less — that is the fix working.
- In the Weather view the days toggle now reads "Show all days".
