FP109.1 INSTALL — Add "touchdown" to the filter
================================================
Files (2 code/test + 3 docs):
  news_store.py
  tests/test_us_sport_filter_fp109.py
  CHANGELOG_FP109.1.txt
  README_INSTALL_FP109.1.txt
  BUNDLE_MANIFEST_FP109.1.txt

No hold: news_store.py is not touched by unpushed FP106/FP108/FP110
work, so this installs and pushes any time.

Install (Termux, from ~/Kaivor):
  1. Back up the file being changed:
       cp news_store.py news_store.py.before-fp109.1
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests:
       python -m pytest tests/test_us_sport_filter_fp109.py -q
     Expected: 27 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 858 passed, 0 failed, 2 skipped.

Push:
  cd ~/Kaivor
  git add news_store.py tests/test_us_sport_filter_fp109.py CHANGELOG_FP109.1.txt README_INSTALL_FP109.1.txt BUNDLE_MANIFEST_FP109.1.txt
  git status --short
  git commit -m "FP109.1: add touchdown to the American-football filter"
  git push

Live check after deploy: the next news refresh drops the
Tennessee/Texas A&M story; searching the homepage for "touchdown"
should find nothing.
