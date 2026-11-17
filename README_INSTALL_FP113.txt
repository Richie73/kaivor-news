FP113 INSTALL — Memories on Postgres
=====================================
Files (4 code + 1 migration + 1 test + 3 docs):
  core/memory/postgres_store.py
  core/memory/api.py
  main.py
  migrations/reading/002_memories_tasks_fp113_fp114.sql
  tests/test_postgres_memory_fp113.py
  CHANGELOG_FP113.txt
  README_INSTALL_FP113.txt
  BUNDLE_MANIFEST_FP113.txt

Note: main.py is shared with FP114/FP115 and templates/index.html
with FP114/FP115; all three milestones install and push together.
The migration was already run in Supabase (17 Nov 2026) — the
file is committed for the record only; do not run it again.

Install (Termux, from ~/Kaivor):
  1. Back up the files being changed:
       cp main.py main.py.before-fp113
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests (combined FP113+FP114+FP115 run):
       python -m pytest tests/test_postgres_memory_fp113.py tests/test_tasks_fp114.py tests/test_auto_remember_fp115.py tests/test_chat_memory_fp112.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py tests/test_morning_hub_fp101.py tests/test_unified_refresh_fp111.py tests/test_type_scale_fp096.py -q
     Expected: 128 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 980 passed, 0 failed, 2 skipped.

Push (combined FP113+FP114+FP115 — see README_INSTALL_FP115.txt
for the full push script).

Live check after deploy: the Memories view still works; a memory
saved now survives the next deploy (SQLite memories from before
the deploy stay in the old store and are not migrated — FP112
had only just shipped, so none are expected).
