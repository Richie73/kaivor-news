FP117 INSTALL — One green across the whole app
================================================
Files (2 templates + 2 tests + 3 docs):
  templates/index.html
  templates/reading.html
  tests/test_one_green_fp117.py
  tests/test_design_system_fp090.py
  CHANGELOG_FP117.txt
  README_INSTALL_FP117.txt
  BUNDLE_MANIFEST_FP117.txt

Install (Termux, from ~/Kaivor):
  1. Back up the files being changed:
       cp templates/index.html templates/index.html.before-fp117
       cp templates/reading.html templates/reading.html.before-fp117
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests:
       python -m pytest tests/test_one_green_fp117.py tests/test_design_system_fp090.py tests/test_type_scale_fp096.py -q
     Expected: 21 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 995 passed, 0 failed, 2 skipped.

Push (only after FP116 is pushed, or combined with it — both
milestones share templates/index.html and templates/reading.html):
  cd ~/Kaivor
  git add templates/index.html templates/reading.html tests/test_one_green_fp117.py tests/test_design_system_fp090.py CHANGELOG_FP117.txt README_INSTALL_FP117.txt BUNDLE_MANIFEST_FP117.txt
  git status --short
  git commit -m "FP117: one green across the whole app"
  git push

Live check after deploy: every green in the app is the Spark
K green — buttons, links, badges, toggles, the market flash
and the Save button. Dark panels and muted text are tints of
that same green.
