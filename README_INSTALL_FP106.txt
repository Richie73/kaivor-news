FP106 install — Met Office Weather Warnings
==============================================

Files in this bundle (9):
  weather_warnings.py
  morning_brief.py
  main.py
  templates/index.html
  render.yaml
  tests/test_weather_warnings_fp106.py
  CHANGELOG_FP106.txt
  README_INSTALL_FP106.txt
  BUNDLE_MANIFEST_FP106.txt

Install (from the Kaivor directory in Termux):

  cd ~/Kaivor
  cp morning_brief.py morning_brief.py.before-fp106
  cp main.py main.py.before-fp106
  cp templates/index.html templates/index.html.before-fp106
  cp render.yaml render.yaml.before-fp106
  # copy the new/changed files into place (Muse installs via SSH)

Test:

  python -m pytest tests/test_weather_warnings_fp106.py -q
  # expected: 15 passed

  python -m pytest tests/ -q
  # expected: 819 passed, 0 failed, 2 skipped

Push (after the phone suite is green):

  git add weather_warnings.py morning_brief.py main.py templates/index.html render.yaml tests/test_weather_warnings_fp106.py CHANGELOG_FP106.txt README_INSTALL_FP106.txt BUNDLE_MANIFEST_FP106.txt
  git commit -m "FP106: Met Office Weather Warnings for Puddington"
  git push

Then set up the key (see CHANGELOG_FP106.txt): DataHub account
+ Warnings plan, or the NSWWS contact form; paste the feed URL
and key into Render as KAIVOR_WARNINGS_FEED_URL and
KAIVOR_WARNINGS_API_KEY.
