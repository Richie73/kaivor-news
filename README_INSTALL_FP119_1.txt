README_INSTALL_FP119_1.txt — Rain radar zoom fix
=================================================

Install: copy templates/index.html and
tests/test_rain_radar_fp119.py over the matching files in
~/Kaivor, then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_rain_radar_fp119.py -q

Expected: 6 passed. Full suite: 1040 passed / 0 failed /
2 skipped (1039 + 1).

No new env var, no migration, no setup. Deploy as usual and
check live: open the Weather view — the radar should show
real rain colours over the map instead of "Zoom Level Not
Supported", and zooming in stops at the closest useful level.
