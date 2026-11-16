FP111 INSTALL — One refresh button, following the view
=====================================================
Files (4 code/test + 3 docs):
  templates/index.html
  tests/test_unified_refresh_fp111.py
  tests/test_news_refresh_button_fp095.py
  tests/test_markets_view_fp086.py
  CHANGELOG_FP111.txt
  README_INSTALL_FP111.txt
  BUNDLE_MANIFEST_FP111.txt

No hold: nothing else unpushed shares these files.

Install (Termux, from ~/Kaivor):
  1. Back up the file being changed:
       cp templates/index.html templates/index.html.before-fp111
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests:
       python -m pytest tests/test_unified_refresh_fp111.py tests/test_news_refresh_button_fp095.py tests/test_markets_view_fp086.py -q
     Expected: 25 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 891 passed, 0 failed, 2 skipped.

Push:
  cd ~/Kaivor
  git add templates/index.html tests/test_unified_refresh_fp111.py tests/test_news_refresh_button_fp095.py tests/test_markets_view_fp086.py CHANGELOG_FP111.txt README_INSTALL_FP111.txt BUNDLE_MANIFEST_FP111.txt
  git status --short
  git commit -m "FP111: one refresh button, following the view"
  git push

Live check after deploy: News shows "Refresh news" in the title
row; Markets shows "Refresh markets" there instead (and no other
refresh buttons); Chat, Saved, Settings, Weather and the Hub show
no refresh button at all; Settings is still in the header.
