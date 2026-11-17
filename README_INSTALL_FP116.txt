FP116 INSTALL — The app is called Kaivor now
=============================================
Files (5 code + 2 tests + 3 docs):
  templates/index.html
  templates/reading.html
  static/manifest.webmanifest
  main.py
  confidence_aware_ai.py
  tests/test_rename_fp116.py
  tests/test_logo_splash_fp083.py
  CHANGELOG_FP116.txt
  README_INSTALL_FP116.txt
  BUNDLE_MANIFEST_FP116.txt

No hold: nothing else unpushed shares these files.

Install (Termux, from ~/Kaivor):
  1. Back up the files being changed:
       cp templates/index.html templates/index.html.before-fp116
       cp templates/reading.html templates/reading.html.before-fp116
       cp main.py main.py.before-fp116
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests:
       python -m pytest tests/test_rename_fp116.py tests/test_logo_splash_fp083.py tests/test_splash_polish_fp097.py tests/test_reading_web_fp042.py -q
     Expected: 27 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 988 passed, 0 failed, 2 skipped.

Push:
  cd ~/Kaivor
  git add templates/index.html templates/reading.html static/manifest.webmanifest main.py confidence_aware_ai.py tests/test_rename_fp116.py tests/test_logo_splash_fp083.py CHANGELOG_FP116.txt README_INSTALL_FP116.txt BUNDLE_MANIFEST_FP116.txt
  git status --short
  git commit -m "FP116: the app is called Kaivor now"
  git push

Live check after deploy: the header says KAIVOR with "Your
personal AI" under it; the browser tab says Kaivor; the splash
says KAIVOR. The home-screen app name comes from the manifest
— if the old name still shows, remove the app from the home
screen and re-add it.
