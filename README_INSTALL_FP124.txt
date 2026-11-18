README_INSTALL_FP124.txt — Rain radar provider switch to LibreWXR
===================================================================

Install: copy templates/index.html and
tests/test_rain_radar_fp119.py over the matching files in
~/Kaivor, then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_rain_radar_fp119.py -q

Expected: 6 passed. Full suite: 1040 passed / 0 failed /
2 skipped (no new tests — the 6 existing radar tests were
updated for the new provider and zoom range).

No new env var, no migration, no setup. Deploy as usual and
check live: open the Weather view — the radar should show
real rain colours, zoomable in to street level detail, with
Play stepping through the past ~2 hours plus a nowcast.
