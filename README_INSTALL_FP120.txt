FP120 INSTALL — Softer brand green (leaf green #3aa76d)
======================================================
Files (7 code/assets + 6 tests + 3 docs):
  templates/index.html
  templates/reading.html
  static/icons/kaivor-logo-v4.svg
  static/icons/kaivor-news-192-v4.png
  static/icons/kaivor-news-512-v4.png
  static/manifest.webmanifest
  static/service-worker.js
  tests/test_design_system_fp090.py
  tests/test_one_green_fp117.py
  tests/test_logo_splash_fp083.py
  tests/test_markets_view_fp086.py
  tests/test_rename_fp116.py
  tests/test_softer_green_fp120.py
  CHANGELOG_FP120.txt
  README_INSTALL_FP120.txt
  BUNDLE_MANIFEST_FP120.txt

Deleted (the old v3 icons — the FP120 test asserts they are gone):
  static/icons/kaivor-logo-v3.svg
  static/icons/kaivor-news-192-v3.png
  static/icons/kaivor-news-512-v3.png

Install (Termux, from ~/Kaivor):
  1. Back up the files being changed:
       cp templates/index.html templates/index.html.before-fp120
       cp templates/reading.html templates/reading.html.before-fp120
  2. Delete the old v3 icon files:
       rm static/icons/kaivor-logo-v3.svg static/icons/kaivor-news-192-v3.png static/icons/kaivor-news-512-v3.png
  3. Copy the new files in (Muse installs them over SSH).
  4. Run the targeted tests:
       python -m pytest tests/test_softer_green_fp120.py tests/test_one_green_fp117.py tests/test_design_system_fp090.py tests/test_logo_splash_fp083.py tests/test_markets_view_fp086.py tests/test_rename_fp116.py -q
     Expected: 46 passed.
  5. Run the full suite:
       python -m pytest -q
     Expected: 1025 passed, 0 failed, 2 skipped.

Push:
  cd ~/Kaivor
  git add templates/index.html templates/reading.html static/manifest.webmanifest static/service-worker.js tests/test_design_system_fp090.py tests/test_one_green_fp117.py tests/test_logo_splash_fp083.py tests/test_markets_view_fp086.py tests/test_rename_fp116.py tests/test_softer_green_fp120.py CHANGELOG_FP120.txt README_INSTALL_FP120.txt BUNDLE_MANIFEST_FP120.txt
  git add -A static/icons/
  git status --short
  git commit -m "FP120: softer brand green (leaf green)"
  git push

Live check after deploy: the served page contains #3aa76d
and no #35FA33; the manifest lists the v4 icons. On the
phone the header, splash and green text should all read as
the calmer leaf green; the home-screen icon should update
to the new colour without a reinstall (new icon URLs).
