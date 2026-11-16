FP105 install — Readwise highlights in Reading
================================================

Files in this bundle (9):
  readwise_client.py
  news_store.py
  main.py
  templates/reading.html
  render.yaml
  tests/test_readwise_highlights_fp105.py
  CHANGELOG_FP105.txt
  README_INSTALL_FP105.txt
  BUNDLE_MANIFEST_FP105.txt

Install (from the Kaivor directory in Termux):

  cd ~/Kaivor
  cp news_store.py news_store.py.before-fp105
  cp main.py main.py.before-fp105
  cp templates/reading.html templates/reading.html.before-fp105
  cp render.yaml render.yaml.before-fp105
  # copy the new/changed files into place (Muse installs via SSH)

Test:

  python -m pytest tests/test_readwise_highlights_fp105.py -q
  # expected: 13 passed

  python -m pytest tests/ -q
  # expected: 804 passed, 0 failed, 2 skipped

Push (after the phone suite is green):

  git add readwise_client.py news_store.py main.py templates/reading.html render.yaml tests/test_readwise_highlights_fp105.py CHANGELOG_FP105.txt README_INSTALL_FP105.txt BUNDLE_MANIFEST_FP105.txt
  git commit -m "FP105: Readwise highlights in Reading"
  git push

Then set up the token (see CHANGELOG_FP105.txt): copy the access
token from readwise.io/access_token into Render as
KAIVOR_READWISE_TOKEN, then tap Sync highlights in Reading.
