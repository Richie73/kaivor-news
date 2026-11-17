FP114 INSTALL — In-app tasks
==============================
Files (3 code + 6 tests + 3 docs):
  tasks_store.py
  main.py
  templates/index.html
  tests/test_tasks_fp114.py
  tests/test_weather_redesign_fp082.py
  tests/test_markets_view_fp086.py
  tests/test_morning_hub_fp101.py
  tests/test_unified_refresh_fp111.py
  tests/test_type_scale_fp096.py
  CHANGELOG_FP114.txt
  README_INSTALL_FP114.txt
  BUNDLE_MANIFEST_FP114.txt

Note: main.py is shared with FP113/FP115 and templates/index.html
with FP115; all three milestones install and push together.

Install (Termux, from ~/Kaivor):
  1. Back up the files being changed:
       cp templates/index.html templates/index.html.before-fp114
       cp main.py main.py.before-fp114
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests (combined FP113+FP114+FP115 run):
       python -m pytest tests/test_postgres_memory_fp113.py tests/test_tasks_fp114.py tests/test_auto_remember_fp115.py tests/test_chat_memory_fp112.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py tests/test_morning_hub_fp101.py tests/test_unified_refresh_fp111.py tests/test_type_scale_fp096.py -q
     Expected: 128 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 980 passed, 0 failed, 2 skipped.

Push (combined FP113+FP114+FP115 — see README_INSTALL_FP115.txt
for the full push script).

Live check after deploy: the Hub has a "✅ Tasks" button; the
Tasks view opens with an add form; GET /api/tasks returns 401
when locked. On the phone (needs the Render PIN): add a task,
tick it done, delete it.
