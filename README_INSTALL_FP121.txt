README_INSTALL_FP121.txt — Today's tasks in the Hub and the morning brief
=========================================================================

Install: copy morning_brief.py, main.py, templates/index.html and
tests/test_tasks_today_fp121.py over the matching files in ~/Kaivor,
then run the targeted tests:

  cd ~/Kaivor
  python -m pytest tests/test_tasks_today_fp121.py tests/test_chat_speech_fp122.py tests/test_work_hours_rain_fp123.py -q

Expected: 14 passed (7 FP121 + 4 FP122 + 3 FP123). Full suite:
1039 passed / 0 failed / 2 skipped (1025 + 14).

No new env var, no migration, no setup. Deploy as usual and
check live: the Hub shows a "Tasks today" card, and the next
06:00 brief lists due tasks in a "Tasks today:" section.
