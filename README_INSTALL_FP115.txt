FP115 INSTALL — Auto-remembering (+ combined FP113+FP114+FP115 push)
=====================================================================
Files (3 code + 1 test + 3 docs):
  auto_remember.py
  main.py
  templates/index.html
  tests/test_auto_remember_fp115.py
  CHANGELOG_FP115.txt
  README_INSTALL_FP115.txt
  BUNDLE_MANIFEST_FP115.txt

Note: main.py is shared with FP113/FP114 and templates/index.html
with FP114; all three milestones install and push together as one
commit (24 files).

Install (Termux, from ~/Kaivor):
  1. Back up the files being changed:
       cp templates/index.html templates/index.html.before-fp115
       cp main.py main.py.before-fp115
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests (combined FP113+FP114+FP115 run):
       python -m pytest tests/test_postgres_memory_fp113.py tests/test_tasks_fp114.py tests/test_auto_remember_fp115.py tests/test_chat_memory_fp112.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py tests/test_morning_hub_fp101.py tests/test_unified_refresh_fp111.py tests/test_type_scale_fp096.py -q
     Expected: 128 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 980 passed, 0 failed, 2 skipped.

Push (one commit for FP113+FP114+FP115):
  cd ~/Kaivor
  git add core/memory/postgres_store.py core/memory/api.py main.py templates/index.html migrations/reading/002_memories_tasks_fp113_fp114.sql tasks_store.py auto_remember.py tests/test_postgres_memory_fp113.py tests/test_tasks_fp114.py tests/test_auto_remember_fp115.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py tests/test_morning_hub_fp101.py tests/test_unified_refresh_fp111.py tests/test_type_scale_fp096.py CHANGELOG_FP113.txt README_INSTALL_FP113.txt BUNDLE_MANIFEST_FP113.txt CHANGELOG_FP114.txt README_INSTALL_FP114.txt BUNDLE_MANIFEST_FP114.txt CHANGELOG_FP115.txt README_INSTALL_FP115.txt BUNDLE_MANIFEST_FP115.txt
  git status --short
  git commit -m "FP113-115: memories on Postgres, in-app tasks, auto-remembering"
  git push

Live check after deploy: the chat form has a "Remember things
from our chats" checkbox (on by default); the Hub has a Tasks
button; GET /api/tasks returns 401 when locked. On the phone
(needs the Render PIN): tell the chat a durable fact, then
check Memories a minute later — it should appear with source
auto. Add a task, tick it done, delete it.
