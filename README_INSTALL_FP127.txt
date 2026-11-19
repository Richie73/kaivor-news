README_INSTALL_FP127.txt — Football in the morning brief
========================================================

No database step. No new env var.

Install: copy these files over the matching files in ~/Kaivor,
then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_football_brief_fp127.py -q

Expected: 13 passed. Full suite: 1104 passed / 0 failed /
2 skipped.

Verify after deploy: the next weekday 06:00 brief lists
today's fixtures and last night's results under "Football:".
The JSON brief (GET /api/automation/brief, cron token) carries
the same lines under "football".
