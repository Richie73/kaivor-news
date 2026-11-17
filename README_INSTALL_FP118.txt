FP118 INSTALL — Task due time + alerts
=======================================
Files (4 code + 2 tests + 1 migration + 3 docs):
  tasks_store.py
  main.py
  templates/index.html
  render.yaml
  tests/test_task_alerts_fp118.py
  tests/test_tasks_fp114.py
  migrations/reading/003_task_due_time_alerts_fp118.sql
  CHANGELOG_FP118.txt
  README_INSTALL_FP118.txt
  BUNDLE_MANIFEST_FP118.txt

Migration 003 is ALREADY RUN (Supabase, 17 Nov evening — the
tables were created statement by statement after the long paste
kept failing; the check query returned both tables). The .sql
file ships here as the versioned record only. Do NOT re-run it
unless the columns are missing (it is IF NOT EXISTS, so a
re-run is harmless).

Install (Termux, from ~/Kaivor):
  1. Back up the files being changed:
       cp templates/index.html templates/index.html.before-fp118
       cp main.py main.py.before-fp118
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests:
       python -m pytest tests/test_task_alerts_fp118.py tests/test_tasks_fp114.py -q
     Expected: 47 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 1016 passed, 0 failed, 2 skipped.

Push:
  cd ~/Kaivor
  git add tasks_store.py main.py templates/index.html render.yaml tests/test_task_alerts_fp118.py tests/test_tasks_fp114.py migrations/reading/003_task_due_time_alerts_fp118.sql CHANGELOG_FP118.txt README_INSTALL_FP118.txt BUNDLE_MANIFEST_FP118.txt
  git status --short
  git commit -m "FP118: task due time and alerts"
  git push

Live check after deploy: POST /api/automation/tasks/due without
a token returns 401; the Tasks form shows a Due time field.
Then Richie's setup (MacroDroid macro, Render webhook URL,
cron-job.org every 15 min) — see CHANGELOG_FP118.txt.
