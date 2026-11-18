README_INSTALL_FP123.txt — Work-hours rain line
================================================

Install: copy templates/index.html and
tests/test_work_hours_rain_fp123.py over the matching files
in ~/Kaivor, then run the targeted tests (combined with
FP121 and FP122):

  cd ~/Kaivor
  python -m pytest tests/test_tasks_today_fp121.py tests/test_chat_speech_fp122.py tests/test_work_hours_rain_fp123.py -q

Expected: 14 passed (7 FP121 + 4 FP122 + 3 FP123). Full suite:
1039 passed / 0 failed / 2 skipped (1025 + 14).

No new env var, no migration, no setup. Deploy as usual and
check live: the Weather view shows one work-hours rain line
under the summary (today's hours before 17:00, tomorrow's
after).
