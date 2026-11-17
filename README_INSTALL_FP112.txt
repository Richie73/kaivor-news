FP112 INSTALL — The chat remembers across sessions
===================================================
Files (6 code + 6 tests + 3 docs):
  core/memory/database.py
  core/memory/models.py
  core/memory/manager.py
  core/memory/api.py
  main.py
  templates/index.html
  tests/test_chat_memory_fp112.py
  tests/test_weather_redesign_fp082.py
  tests/test_markets_view_fp086.py
  tests/test_morning_hub_fp101.py
  tests/test_unified_refresh_fp111.py
  tests/test_type_scale_fp096.py
  CHANGELOG_FP112.txt
  README_INSTALL_FP112.txt
  BUNDLE_MANIFEST_FP112.txt

No hold: nothing else unpushed shares these files.

Install (Termux, from ~/Kaivor):
  1. Back up the files being changed:
       cp templates/index.html templates/index.html.before-fp112
       cp main.py main.py.before-fp112
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests:
       python -m pytest tests/test_chat_memory_fp112.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py tests/test_morning_hub_fp101.py tests/test_unified_refresh_fp111.py tests/test_type_scale_fp096.py -q
     Expected: 70 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 922 passed, 0 failed, 2 skipped.

Push:
  cd ~/Kaivor
  git add core/memory/database.py core/memory/models.py core/memory/manager.py core/memory/api.py main.py templates/index.html tests/test_chat_memory_fp112.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py tests/test_morning_hub_fp101.py tests/test_unified_refresh_fp111.py tests/test_type_scale_fp096.py CHANGELOG_FP112.txt README_INSTALL_FP112.txt BUNDLE_MANIFEST_FP112.txt
  git status --short
  git commit -m "FP112: chat memory — Remember button, Memories view, recall in chat"
  git push

Live check after deploy: in Chat, an assistant reply shows a
"Remember this" button; the chat card has a "Memories"
button; GET /api/memories returns 401 when locked. On the
phone (needs the Render PIN): tap "Remember this" on a
reply, open Memories to see it listed, then ask a question
about it in a fresh chat and check the reply uses it.
