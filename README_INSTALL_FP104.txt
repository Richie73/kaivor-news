FP104 install — morning brief for phone automation
================================================

Files in this bundle (8):
  morning_brief.py
  main.py
  templates/index.html
  render.yaml
  tests/test_morning_brief_fp104.py
  CHANGELOG_FP104.txt
  README_INSTALL_FP104.txt
  BUNDLE_MANIFEST_FP104.txt

Install (from the Kaivor directory in Termux):

  cd ~/Kaivor
  cp main.py main.py.before-fp104
  cp templates/index.html templates/index.html.before-fp104
  cp render.yaml render.yaml.before-fp104
  # copy the new/changed files into place (Muse installs via SSH)

Test:

  python -m pytest tests/test_morning_brief_fp104.py -q
  # expected: 15 passed

  python -m pytest tests/ -q
  # expected: 791 passed, 0 failed, 2 skipped

Push (after the phone suite is green):

  git add morning_brief.py main.py templates/index.html render.yaml tests/test_morning_brief_fp104.py CHANGELOG_FP104.txt README_INSTALL_FP104.txt BUNDLE_MANIFEST_FP104.txt
  git commit -m "FP104: morning brief automation for MacroDroid and Tasker"
  git push

Then set up the phone side (see CHANGELOG_FP104.txt): MacroDroid
webhook trigger URL into Render as KAIVOR_MACRODROID_WEBHOOK_URL,
and a cron-job.org job for the send endpoint.
