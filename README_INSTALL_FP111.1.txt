FP111.1 INSTALL — The header no longer hides the top of the page
==================================================================
Files (3 code/test + 3 docs):
  templates/index.html
  tests/test_sticky_header_fp111.py
  tests/test_design_system_fp090.py
  CHANGELOG_FP111.1.txt
  README_INSTALL_FP111.1.txt
  BUNDLE_MANIFEST_FP111.1.txt

No hold: nothing else unpushed shares these files.

Install (Termux, from ~/Kaivor):
  1. Back up the file being changed:
       cp templates/index.html templates/index.html.before-fp111.1
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests:
       python -m pytest tests/test_sticky_header_fp111.py tests/test_design_system_fp090.py -q
     Expected: 11 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 894 passed, 0 failed, 2 skipped.

Push:
  cd ~/Kaivor
  git add templates/index.html tests/test_sticky_header_fp111.py tests/test_design_system_fp090.py CHANGELOG_FP111.1.txt README_INSTALL_FP111.1.txt BUNDLE_MANIFEST_FP111.1.txt
  git status --short
  git commit -m "FP111.1: sticky header so it stops hiding the market panel"
  git push

Live check after deploy: the "MARKET WATCH" heading shows in
full at the top of the home view, with a small gap under the
header; scrolling still keeps the header pinned at the top.
