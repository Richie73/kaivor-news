README_INSTALL_FP122.txt — Chat replies read aloud
===================================================

Install: copy templates/index.html and
tests/test_chat_speech_fp122.py over the matching files in
~/Kaivor, then run the targeted tests (combined with FP121
and FP123):

  cd ~/Kaivor
  python -m pytest tests/test_tasks_today_fp121.py tests/test_chat_speech_fp122.py tests/test_work_hours_rain_fp123.py -q

Expected: 14 passed (7 FP121 + 4 FP122 + 3 FP123). Full suite:
1039 passed / 0 failed / 2 skipped (1025 + 14).

No new env var, no migration, no setup. Deploy as usual and
check live: each assistant reply in the chat hub has a
Listen button that reads it aloud; tapping it again stops.
