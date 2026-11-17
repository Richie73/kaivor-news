FP119 INSTALL — Rain radar in the Weather view
=============================================
Files (1 code + 1 test + 3 docs):
  templates/index.html
  tests/test_rain_radar_fp119.py
  CHANGELOG_FP119.txt
  README_INSTALL_FP119.txt
  BUNDLE_MANIFEST_FP119.txt

Install (Termux, from ~/Kaivor):
  1. Back up the file being changed:
       cp templates/index.html templates/index.html.before-fp119
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests:
       python -m pytest tests/test_rain_radar_fp119.py tests/test_weather_redesign_fp082.py tests/test_design_system_fp090.py tests/test_type_scale_fp096.py -q
     Expected: 30 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 1021 passed, 0 failed, 2 skipped.

Push:
  cd ~/Kaivor
  git add templates/index.html tests/test_rain_radar_fp119.py CHANGELOG_FP119.txt README_INSTALL_FP119.txt BUNDLE_MANIFEST_FP119.txt
  git status --short
  git commit -m "FP119: rain radar in the Weather view"
  git push

Live check after deploy: the served page contains the Leaflet
tags, #rain-radar-map, loadRainRadar and the Play button.
The map itself only renders on a real phone (it needs the
Leaflet script + the RainViewer feed): open Weather in Kaivor
and the radar should show over the Wirral, with Play stepping
through the last ~2 hours.
