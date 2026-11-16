FP109 INSTALL — Exclude American-football and baseball stories
================================================================
Files (2 code/test + 3 docs):
  news_store.py
  tests/test_us_sport_filter_fp109.py
  CHANGELOG_FP109.txt
  README_INSTALL_FP109.txt
  BUNDLE_MANIFEST_FP109.txt

Install (Termux, from ~/Kaivor):
  1. Back up the file being changed:
       cp news_store.py news_store.py.before-fp109
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests:
       python -m pytest tests/test_us_sport_filter_fp109.py -q
     Expected: 25 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 856 passed, 0 failed, 2 skipped.

Push (after FP106 and FP107 — FP109 touches different files, so the
order does not matter for the code, but one push at a time keeps the
history clean):
  cd ~/Kaivor
  git add news_store.py tests/test_us_sport_filter_fp109.py CHANGELOG_FP109.txt README_INSTALL_FP109.txt BUNDLE_MANIFEST_FP109.txt
  git status --short
  git commit -m "FP109: exclude American-football and baseball stories from the feed"
  git push

Live check after deploy: the next news refresh drops the stories (the
current cache clears on refresh — tap "Refresh news" in Kaivor or wait
for the next automatic refresh). Verify by searching the homepage for
"NFL" / "MLB": both should be gone, while football (soccer) stories
remain.
